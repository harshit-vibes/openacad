"""Meta-Evaluator loop — proposes hardened system prompts from accumulated rubric events.

Active only in `evolving-notes` (and any other scenario where `has_meta_eval=True`).
After ≥N rubric events for a role, the Meta-Evaluator agent is asked to produce
a new system prompt. The proposal is written to the prompts table as `state=proposed`
plus an on-disk `<role>.v{N+1}.md` file. Scholar promotes via `promote_prompt(version)`.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel
from pydantic_ai import Agent

from openacad.runtime.settings import settings
from openacad.runtime.scenario import AgentRole, active_scenario
from openacad.runtime.llm import model_for, settings_for
from openacad.feedback.schema import EvalEvent, PromptVersion
from openacad.runtime import db
from openacad.feedback import rubric
class MetaProposal(BaseModel):
    new_body: str
    rationale: str


def _build_agent_with_prompt(body: str) -> Agent:
    return Agent(
        model_for("synthesis"),
        system_prompt=body,
        output_type=MetaProposal,
        retries=1,
        model_settings=settings_for("synthesis"),
    )


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PromptProposal(BaseModel):
    role: AgentRole
    new_version: str
    body: str
    rationale: str
    based_on_event_ids: list[str]


def _next_version(role: AgentRole) -> tuple[int, str]:
    """Find the highest v{N} for this role in the active scenario; return next."""
    prompts = db.list_prompts(name=role.value)
    nums = []
    for p in prompts:
        try:
            n = int(p.version.split(".v")[-1])
            nums.append(n)
        except (ValueError, IndexError):
            pass
    nxt = max(nums + [0]) + 1
    return nxt, f"{role.value}.v{nxt}"


def _build_user_prompt(role: AgentRole, current_body: str,
                       rubrics: list[rubric.Rubric]) -> str:
    """Compose the brief the Meta-Evaluator agent answers."""
    bits = [f"## Role being improved\n{role.value}"]
    bits.append("\n## Current system prompt\n```\n" + current_body.strip() + "\n```")
    bits.append(f"\n## Rubric ratings ({len(rubrics)} samples)")
    for r in rubrics[:15]:
        crit = ", ".join(f"{k}={v}" for k, v in r.criteria.items())
        bits.append(f"- overall={r.overall}; {crit}; reason: {r.free_text[:200]!r}")
    avg = rubric.role_average(role)
    bits.append(f"\nAggregate: count={avg['count']}, overall_avg={avg['overall_avg']}, per_criterion={avg['criteria_avg']}")
    bits.append(
        "\n## Task\nPropose a new system prompt that addresses the lowest-rated "
        "criteria and most-common reject reasons. Keep what works. Return both the "
        "new body and a 2-3 sentence rationale."
    )
    return "\n".join(bits)


def propose_new_prompt(role: AgentRole) -> PromptProposal | None:
    """Run the Meta-Evaluator agent; write the proposal to disk + DB. Returns None
    if not enough rubric events accumulated."""
    s = active_scenario()
    if not s.has_meta_eval:
        raise RuntimeError(
            f"scenario {s.key} does not have meta-eval enabled "
            f"(only Evolving Notes does in v1)"
        )

    threshold = settings.prompt_regen_threshold
    rubs = rubric.list_for_role(role, limit=200)
    if len(rubs) < threshold:
        return None

    current_prompts = [p for p in db.list_prompts(name=role.value) if p.state == "active"]
    if not current_prompts:
        # fallback to v1 from disk
        path = s.prompts_dir / f"{role.value}.v1.md"
        current_body = path.read_text(encoding="utf-8") if path.exists() else "(no prior prompt)"
        current_version = f"{role.value}.v1"
    else:
        active = sorted(current_prompts, key=lambda p: p.created_at, reverse=True)[0]
        current_body = active.body
        current_version = active.version

    from openacad.runtime.agent_base import build_meta_evaluator
    agent = build_meta_evaluator()
    user_prompt = _build_user_prompt(role, current_body, rubs)
    result = agent.run_sync(user_prompt)
    out = result.output  # MetaProposal(new_body, rationale)

    nxt_n, new_version = _next_version(role)

    # Persist on disk
    fn = s.prompts_dir / f"{role.value}.v{nxt_n}.md"
    fn.write_text(out.new_body, encoding="utf-8")

    # Persist in DB as proposed
    pv = PromptVersion(
        name=role.value,
        version=new_version,
        created_at=_now(),
        body=out.new_body,
        parent_version=current_version,
        state="proposed",
        based_on_events=[],
    )
    db.upsert_prompt(pv)

    # Log event
    db.log_event(EvalEvent(
        id=f"ev-{uuid.uuid4().hex[:8]}",
        timestamp=_now(),
        kind="prompt_propose",
        actor="meta_evaluator",
        payload={
            "scenario": s.key,
            "role": role.value,
            "new_version": new_version,
            "parent_version": current_version,
            "rationale": out.rationale,
            "n_rubrics": len(rubs),
        },
    ))

    return PromptProposal(
        role=role,
        new_version=new_version,
        body=out.new_body,
        rationale=out.rationale,
        based_on_event_ids=[r.id for r in rubs[:20]],
    )


def promote_prompt(version: str) -> dict:
    """Mark a proposed prompt as active (archives the previously-active one).
    Busts the agent_factory cache so the next agent build picks up the new prompt."""
    prompts = db.list_prompts()
    match = next((p for p in prompts if p.version == version), None)
    if not match:
        raise ValueError(f"prompt version {version} not found in active scenario")

    db.archive_active_prompts(match.name)
    db.update_prompt_state(version, "active")

    role = AgentRole(match.name)
    from openacad.hooks.on_prompt_promoted import fire as fire_on_prompt_promoted
    fire_on_prompt_promoted(role)

    db.log_event(EvalEvent(
        id=f"ev-{uuid.uuid4().hex[:8]}",
        timestamp=_now(),
        kind="prompt_promote",
        actor="scholar",
        payload={
            "scenario": active_scenario().key,
            "role": match.name,
            "version": version,
        },
    ))
    return {"ok": True, "version": version, "role": match.name}
