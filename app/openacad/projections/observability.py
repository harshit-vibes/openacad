"""Observability projection — tool calls, latency histogram, cost rollups,
activity feed, error log.

Pricing assumption (per spec section 3):
    gpt-4o-mini → $0.15/M input tokens, $0.60/M output tokens.

Cost is computed off `ComparisonResult.tokens_in/out` because tool_calls do
not carry token counts. We bucket the spend two ways:

- **By role**  — derived from the agent that owns the tool_calls referenced
  by the comparison. If a comparison has no tool_call_ids (synthesis-only
  pipelines) we fall back to the `pipeline` label so the rollup is never
  silently empty.
- **By day**   — the date prefix of `run_at`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

from openacad.runtime import db
from openacad.runtime.scenario import use_scenario

from openacad.projections._models import (
    ActivityFeedItem,
    CostRollupItem,
    LatencyBucket,
    ObservabilityView,
    ToolCallRow,
)


# Pricing (USD per token) — gpt-4o-mini.
_INPUT_PRICE = 0.15 / 1_000_000
_OUTPUT_PRICE = 0.60 / 1_000_000


# Latency buckets per the spec (upper bound in ms).
# The last bucket is "10000+"; we use a large sentinel for its upper bound.
_LATENCY_BUCKETS: list[int] = [100, 250, 500, 1000, 2500, 5000, 10000, 10_000_000]


def _cost(tokens_in: int, tokens_out: int) -> float:
    return tokens_in * _INPUT_PRICE + tokens_out * _OUTPUT_PRICE


def _tool_call_to_row(t) -> ToolCallRow:
    # `error_message` is added by the parallel schema migration (Agent S).
    # Read it defensively so the projection is forward-compatible.
    err = getattr(t, "error_message", None)
    return ToolCallRow(
        id=t.id,
        session_id=t.session_id,
        agent=t.agent,
        tool_name=t.tool_name,
        arguments=t.arguments or {},
        n_results=t.n_results,
        latency_ms=t.latency_ms,
        timestamp=t.timestamp,
        error_message=err,
    )


def _bucket_latencies(latencies: Iterable[int]) -> list[LatencyBucket]:
    counts = [0] * len(_LATENCY_BUCKETS)
    for ms in latencies:
        for i, upper in enumerate(_LATENCY_BUCKETS):
            if ms < upper:
                counts[i] += 1
                break
        else:  # >= last sentinel; fold into the final bucket
            counts[-1] += 1
    return [
        LatencyBucket(upper_ms=upper, count=count)
        for upper, count in zip(_LATENCY_BUCKETS, counts)
    ]


def _cost_by_role(comparisons, tool_calls_by_id) -> list[CostRollupItem]:
    """Roll up cost per agent role; fall back to pipeline label when no tool calls."""
    sums: dict[str, dict[str, int]] = {}
    for c in comparisons:
        # Determine roles touched by this comparison.
        roles: list[str] = []
        for tcid in (c.tool_call_ids or []):
            tc = tool_calls_by_id.get(tcid)
            if tc is not None:
                roles.append(tc.agent)
        if not roles:
            # Fallback: use the pipeline tag (e.g. "A", "B1") so this never
            # silently swallows seeded data.
            roles = [c.pipeline]
        # Allocate the full token spend to *each* role touched (cost rollups
        # in this console are descriptive, not strictly additive).
        for role in set(roles):
            bucket = sums.setdefault(role, {"in": 0, "out": 0})
            bucket["in"] += c.tokens_in
            bucket["out"] += c.tokens_out
    out = [
        CostRollupItem(
            bucket_label=role,
            tokens_in=v["in"],
            tokens_out=v["out"],
            cost_usd=_cost(v["in"], v["out"]),
        )
        for role, v in sums.items()
    ]
    out.sort(key=lambda x: x.cost_usd, reverse=True)
    return out


def _cost_by_day(comparisons) -> list[CostRollupItem]:
    sums: dict[str, dict[str, int]] = {}
    for c in comparisons:
        day = c.run_at.date().isoformat()
        bucket = sums.setdefault(day, {"in": 0, "out": 0})
        bucket["in"] += c.tokens_in
        bucket["out"] += c.tokens_out
    out = [
        CostRollupItem(
            bucket_label=day,
            tokens_in=v["in"],
            tokens_out=v["out"],
            cost_usd=_cost(v["in"], v["out"]),
        )
        for day, v in sums.items()
    ]
    out.sort(key=lambda x: x.bucket_label)
    return out


def _build_activity_feed(
    events,
    tool_call_rows: list[ToolCallRow],
    active_prompts,
) -> list[ActivityFeedItem]:
    """Merge events + recent tool calls + active prompt promotions into one
    chronological feed.
    """
    items: list[ActivityFeedItem] = []

    # Recent events (already newest first from list_events).
    for ev in events:
        payload = ev.payload or {}
        if ev.kind == "rubric":
            summary = (
                f"Rubric ({payload.get('role', '?')}): "
                f"overall {payload.get('overall', '?')}"
            )
        elif ev.kind in ("accept", "edit", "reject", "deprecate"):
            summary = f"Verdict: {ev.kind} on {payload.get('draft_id', '?')}"
        elif ev.kind == "prompt_promote":
            summary = (
                f"Promoted prompt {payload.get('role', '?')}:"
                f"{payload.get('version', '?')}"
            )
        elif ev.kind == "prompt_propose":
            summary = (
                f"Meta-eval proposed prompt change for "
                f"{payload.get('target_role') or payload.get('role') or '?'}"
            )
        else:
            summary = ev.kind
        items.append(
            ActivityFeedItem(
                timestamp=ev.timestamp,
                kind=ev.kind,
                actor=ev.actor or "scholar",
                summary=summary,
                detail=payload if isinstance(payload, dict) else {"raw": str(payload)},
            )
        )

    # Recent tool calls — take the last 50 already converted to DTOs.
    last_tcs = sorted(tool_call_rows, key=lambda t: t.timestamp, reverse=True)[:50]
    for t in last_tcs:
        items.append(
            ActivityFeedItem(
                timestamp=t.timestamp,
                kind="tool_call",
                actor=t.agent,
                summary=f"{t.agent} called {t.tool_name} ({t.n_results} results, {t.latency_ms}ms)",
                detail={
                    "tool_call_id": t.id,
                    "session_id": t.session_id,
                    "tool_name": t.tool_name,
                    "n_results": t.n_results,
                    "latency_ms": t.latency_ms,
                    "error_message": t.error_message,
                },
            )
        )

    # Active prompts (last promotion per role).
    for p in active_prompts:
        items.append(
            ActivityFeedItem(
                timestamp=p.created_at,
                kind="prompt_active",
                actor="meta_evaluator",
                summary=f"Active prompt {p.name}:{p.version}",
                detail={
                    "name": p.name,
                    "version": p.version,
                    "parent_version": p.parent_version,
                    "state": p.state,
                },
            )
        )

    items.sort(key=lambda x: x.timestamp, reverse=True)
    return items


def observability_rollup(scenario_key: str = "evolving-notes") -> ObservabilityView:
    with use_scenario(scenario_key):
        tcs = db.list_tool_calls()
        tool_call_rows = [_tool_call_to_row(t) for t in tcs]
        comparisons = db.list_comparisons()
        events = db.list_events(limit=100)
        active_prompts = [p for p in db.list_prompts() if p.state == "active"]

        # Indexes for cost rollup.
        tool_calls_by_id = {t.id: t for t in tcs}

        # Latency histogram across every tool call.
        histogram = _bucket_latencies(t.latency_ms for t in tcs)

        cost_role = _cost_by_role(comparisons, tool_calls_by_id)
        cost_day = _cost_by_day(comparisons)

        # KPI scalars.
        n_tool_calls = len(tool_call_rows)
        total_latency = sum(t.latency_ms for t in tool_call_rows)
        avg_latency = (total_latency / n_tool_calls) if n_tool_calls else 0.0
        total_cost = sum(_cost(c.tokens_in, c.tokens_out) for c in comparisons)

        errors = [t for t in tool_call_rows if t.error_message]
        n_errors = len(errors)

        feed = _build_activity_feed(events, tool_call_rows, active_prompts)

        return ObservabilityView(
            tool_calls=tool_call_rows,
            latency_histogram=histogram,
            cost_by_role=cost_role,
            cost_by_day=cost_day,
            activity_feed=feed,
            errors=errors,
            n_tool_calls=n_tool_calls,
            avg_latency_ms=avg_latency,
            total_cost_usd=total_cost,
            n_errors=n_errors,
        )
