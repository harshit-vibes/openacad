"""Shared Streamlit widgets used across pages."""

from __future__ import annotations

from typing import Any

import streamlit as st

from openacad.runtime.scenario import SCENARIOS, AgentRole, Scenario, Tier, active_scenario
from openacad.feedback import rubric
def scenario_pill(s: Scenario) -> str:
    tier_emoji = {Tier.COLD: "🥶", Tier.CHUNK: "🧩", Tier.ATOMS: "⚛️"}
    return f"{tier_emoji[s.tier]} {s.name}"


def scenario_picker(key: str = "scenario_picker") -> Scenario:
    """Sidebar select that drives the active scenario for the page."""
    options = [s.key for s in SCENARIOS]
    labels = {s.key: scenario_pill(s) for s in SCENARIOS}
    current = st.session_state.get("active_scenario_key", "curated-notes")
    pick = st.sidebar.selectbox(
        "Active scenario",
        options=options,
        index=options.index(current),
        format_func=lambda k: labels[k],
        key=key,
    )
    st.session_state["active_scenario_key"] = pick
    return next(s for s in SCENARIOS if s.key == pick)


def agent_box(role: AgentRole, prompt_version: str | None = None) -> None:
    role_emoji = {
        AgentRole.ANSWERER: "💬",
        AgentRole.EXTRACTOR: "🪓",
        AgentRole.SCORER: "🎯",
        AgentRole.META_EVAL: "🧬",
    }
    label = f"{role_emoji[role]} {role.value}"
    if prompt_version:
        label += f" ({prompt_version})"
    st.markdown(
        f"""<div style='border:1px solid #ccc; border-radius:8px; padding:8px 12px;
        background:#f7f7f9; display:inline-block; margin-right:6px;'>
        {label}</div>""",
        unsafe_allow_html=True,
    )


def agent_map(s: Scenario, active_versions: dict[AgentRole, str] | None = None) -> None:
    """Render the scenario's agents as a horizontal row of boxes."""
    cols = st.columns(len(s.agents))
    for col, role in zip(cols, s.agents):
        with col:
            version = (active_versions or {}).get(role)
            agent_box(role, prompt_version=version)


def metric_strip(metrics: dict[str, Any]) -> None:
    """Display top-line metrics in a horizontal row."""
    items = list(metrics.items())
    cols = st.columns(len(items))
    for col, (label, val) in zip(cols, items):
        col.metric(label, val)


def answer_card(answer: str, citations: list[str], tokens: dict[str, int] | None = None) -> None:
    st.markdown("**Answer**")
    st.markdown(answer)
    if citations:
        st.caption("Cited: " + ", ".join(f"`{c}`" for c in citations[:10])
                   + (f" (+{len(citations)-10} more)" if len(citations) > 10 else ""))
    if tokens:
        bits = [f"{k}={v}" for k, v in tokens.items()]
        st.caption(" · ".join(bits))


def rubric_input(
    *,
    role: AgentRole,
    target_id: str,
    criteria_keys: list[str],
    key_prefix: str = "rubric",
) -> None:
    """Render a 1-5 overall + per-criterion + free-text. Submit writes to db."""
    with st.expander("Rate this answer (rubric)"):
        with st.form(key=f"{key_prefix}-{target_id}", clear_on_submit=True):
            overall = st.slider("Overall (1-5)", 1, 5, 4, key=f"{key_prefix}-{target_id}-overall")
            crits: dict[str, int] = {}
            cols = st.columns(len(criteria_keys)) if criteria_keys else []
            for col, ck in zip(cols, criteria_keys):
                crits[ck] = col.slider(ck, 1, 5, 3, key=f"{key_prefix}-{target_id}-{ck}")
            free_text = st.text_area("Comments / reasons", key=f"{key_prefix}-{target_id}-ft")
            if st.form_submit_button("Submit rubric"):
                r = rubric.Rubric(
                    role=role, target_id=target_id, overall=overall,
                    criteria=crits, free_text=free_text or "",
                )
                rubric.record(r)
                stats = rubric.role_average(role)
                st.success(
                    f"Recorded. {role.value} now has {stats['count']} ratings "
                    f"(overall avg {stats['overall_avg']})."
                )


def next_step(label: str, target: str) -> None:
    """Legacy: render a 'Next →' CTA at the bottom of a walkthrough page.
    Superseded by `nav_footer` which adds Previous + dual-button layout.
    Kept for back-compat with pages not yet migrated."""
    st.divider()
    cols = st.columns([3, 1])
    with cols[1]:
        if st.button(f"Next → {label}", type="primary", use_container_width=True):
            st.switch_page(target)


def act_banner(act: str, title: str, blurb: str) -> None:
    """Legacy top-of-page banner. Superseded by `page_header`."""
    st.caption(f"**{act}**")
    st.title(title)
    st.markdown(blurb)


# ── New layout primitives (scholarly redesign) ──────────────────────────


_TIER_COLOR = {
    Tier.COLD: "#3b82f6",   # blue
    Tier.CHUNK: "#10b981",  # green
    Tier.ATOMS: "#a855f7",  # purple
}


def active_scenario_chip() -> None:
    """Inline pill showing the current active scenario; rendered in the page hero."""
    s = active_scenario()
    color = _TIER_COLOR.get(s.tier, "#666")
    tier_emoji = {Tier.COLD: "🥶", Tier.CHUNK: "🧩", Tier.ATOMS: "⚛️"}[s.tier]
    n_agents = len(s.agents)
    label = f"{tier_emoji} {s.name} · {n_agents} agent{'s' if n_agents != 1 else ''}"
    st.markdown(
        f"""<div style='display:inline-block; border:1px solid {color};
        background:{color}22; color:{color}; padding:4px 12px; border-radius:14px;
        font-size:0.85em; font-weight:600;'>{label}</div>""",
        unsafe_allow_html=True,
    )


def page_header(
    title: str,
    blurb: str,
    hero_metrics: list[tuple[str, str | int]] | None = None,
    show_scenario_chip: bool = True,
) -> None:
    """Consistent page hero: scenario chip + title + blurb + optional metric strip."""
    if show_scenario_chip:
        active_scenario_chip()
    st.title(title)
    st.markdown(blurb)
    if hero_metrics:
        cols = st.columns(len(hero_metrics))
        for col, (label, value) in zip(cols, hero_metrics):
            col.metric(label, value)
    st.divider()


def under_the_hood(label: str = "🔬 Under the hood — agents, prompts, mechanics"):
    """Collapsible 'demo plumbing' container. Use as a context manager:

        with under_the_hood():
            agent_map(s)
            st.json(...)

    Keeps the scholar narrative clean above; the curious can open the drawer."""
    return st.expander(label, expanded=False)


def nav_footer(
    prev_page: str | None = None,
    next_page: str | None = None,
    prev_label: str = "",
    next_label: str = "",
) -> None:
    """Consistent page footer with Previous / Next CTAs."""
    st.divider()
    cols = st.columns([1, 4, 1])
    with cols[0]:
        if prev_page:
            if st.button(f"← {prev_label or 'Previous'}", use_container_width=True):
                st.switch_page(prev_page)
    with cols[2]:
        if next_page:
            if st.button(f"{next_label or 'Next'} →", type="primary",
                         use_container_width=True):
                st.switch_page(next_page)


# ── scenario-aware navigation ───────────────────────────────────────────


WELCOME_PAGE = "walkthrough/00_welcome.py"
CONCLUSION_PAGE = "walkthrough/90_conclusion.py"


def scenario_nav_footer(current_page: str) -> None:
    """Footer whose prev/next adapt to the active scenario's `steps` list.

    Linear flow per scenario:
        Welcome → step[0] → step[1] → … → step[-1] → Conclusion → Welcome

    If `current_page` is not in the active scenario's steps (e.g. the user
    is on a scenario-specific page that the new scenario doesn't expose),
    we fall back to Library → Conclusion.
    """
    s = active_scenario()
    steps = s.steps
    paths = [st_.page_path for st_ in steps]

    prev_page: str | None
    next_page: str | None
    prev_label = ""
    next_label = ""

    if current_page == WELCOME_PAGE:
        prev_page = None
        next_page = paths[0] if paths else CONCLUSION_PAGE
        next_label = steps[0].title if paths else "Conclusion"
    elif current_page == CONCLUSION_PAGE:
        prev_page = paths[-1] if paths else WELCOME_PAGE
        prev_label = steps[-1].title if paths else "Welcome"
        next_page = WELCOME_PAGE
        next_label = "Start over"
    elif current_page in paths:
        idx = paths.index(current_page)
        if idx == 0:
            prev_page = WELCOME_PAGE
            prev_label = "Welcome"
        else:
            prev_page = paths[idx - 1]
            prev_label = steps[idx - 1].title
        if idx == len(paths) - 1:
            next_page = CONCLUSION_PAGE
            next_label = "Conclusion"
        else:
            next_page = paths[idx + 1]
            next_label = steps[idx + 1].title
    else:
        # Page not in this scenario's flow — likely a degraded view that the
        # scenario doesn't normally show. Send the user back to Library and
        # forward to Conclusion.
        prev_page = paths[0] if paths else WELCOME_PAGE
        prev_label = steps[0].title if paths else "Welcome"
        next_page = CONCLUSION_PAGE
        next_label = "Conclusion"

    nav_footer(
        prev_page=prev_page,
        next_page=next_page,
        prev_label=prev_label,
        next_label=next_label,
    )


def status_chip(label: str, kind: str = "neutral") -> str:
    colors = {
        "ok": "#1f7a1f", "warn": "#a06000", "err": "#a01010", "neutral": "#666",
    }
    c = colors.get(kind, colors["neutral"])
    return (
        f"<span style='border:1px solid {c}; color:{c}; padding:2px 8px; "
        f"border-radius:10px; font-size:0.8em;'>{label}</span>"
    )
