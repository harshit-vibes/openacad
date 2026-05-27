"""Observability projection routes for the Next.js playground.

We read ``.openacad/activity.jsonl`` directly so the Next.js UI can show
event counts, latency buckets (when available), and the most recent
activity feed without depending on the legacy ``runtime.db`` scenario
machinery.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query

from openacad.server.deps import get_vault
from openacad.vault import Vault

router = APIRouter()


_LATENCY_BUCKETS_MS = [100, 250, 500, 1000, 2500, 5000, 10000]
"""Upper bounds (ms) for latency histograms. Anything above the last bucket
is captured in the overflow bucket labelled ``> 10000``."""


def _iter_activity(vault: Vault) -> list[dict[str, Any]]:
    """Parse all activity.jsonl events (best-effort: skip malformed lines)."""
    path = vault.sidecar / "activity.jsonl"
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:  # noqa: BLE001
                continue
    return out


def _date_prefix(ts: str | None) -> str:
    if not ts:
        return "unknown"
    try:
        return ts[:10]  # YYYY-MM-DD
    except Exception:  # noqa: BLE001
        return "unknown"


def _bucket_latency_ms(value: float | int) -> str:
    for ub in _LATENCY_BUCKETS_MS:
        if value <= ub:
            return f"≤ {ub}"
    return f"> {_LATENCY_BUCKETS_MS[-1]}"


@router.get("/observability")
def observability(
    limit: int = Query(default=50, ge=1, le=500),
    vault: Vault = Depends(get_vault),
) -> dict[str, Any]:
    events = _iter_activity(vault)

    # KPIs
    event_kinds = Counter(e.get("kind") or e.get("event") or "unknown" for e in events)
    by_day: Counter[str] = Counter()
    by_agent: Counter[str] = Counter()
    latency_hist: Counter[str] = Counter()

    latencies: list[float] = []
    total_cost = 0.0

    for e in events:
        by_day[_date_prefix(e.get("ts") or e.get("at") or e.get("timestamp"))] += 1
        agent = e.get("agent")
        if agent:
            by_agent[str(agent)] += 1
        lat = e.get("latency_ms") or e.get("duration_ms")
        if isinstance(lat, (int, float)):
            latencies.append(float(lat))
            latency_hist[_bucket_latency_ms(float(lat))] += 1
        cost = e.get("cost_usd")
        if isinstance(cost, (int, float)):
            total_cost += float(cost)

    # Most recent N for the activity feed.
    feed = list(reversed(events[-limit:]))

    # Build ordered histogram (preserve bucket order).
    histogram = [
        {"bucket": f"≤ {ub}", "count": latency_hist.get(f"≤ {ub}", 0)}
        for ub in _LATENCY_BUCKETS_MS
    ]
    histogram.append({
        "bucket": f"> {_LATENCY_BUCKETS_MS[-1]}",
        "count": latency_hist.get(f"> {_LATENCY_BUCKETS_MS[-1]}", 0),
    })

    return {
        "n_events": len(events),
        "by_kind": [{"kind": k, "count": v} for k, v in event_kinds.most_common()],
        "by_agent": [{"agent": k, "count": v} for k, v in by_agent.most_common()],
        "by_day": [{"day": k, "count": v} for k, v in sorted(by_day.items())],
        "latency_histogram": histogram,
        "latency": {
            "n": len(latencies),
            "avg_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0,
            "max_ms": max(latencies) if latencies else 0,
        },
        "cost": {
            "total_usd": round(total_cost, 4),
        },
        "feed": feed,
    }


@router.get("/health")
def projection_health(vault: Vault = Depends(get_vault)) -> dict[str, Any]:
    """Quick health probe for the projection — useful for `/observability`."""
    activity_path = vault.sidecar / "activity.jsonl"
    return {
        "vault_path": str(vault.path),
        "sidecar_exists": vault.sidecar.exists(),
        "activity_log_exists": activity_path.exists(),
        "activity_log_bytes": activity_path.stat().st_size if activity_path.exists() else 0,
        "checked_at": datetime.utcnow().isoformat() + "Z",
    }
