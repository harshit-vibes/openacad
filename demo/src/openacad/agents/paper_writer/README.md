# paper_writer agent — slot (not yet implemented)

This directory **reserves a slot** in the harness for a future agent that drafts
long-form research papers from the curated atomic-notes vault. No `agent.py` is
present yet; the harness will only see this agent once it's added.

## When to build this
After the demo's progressive-ladder scenarios have proven that
atoms-attrs-rels + atom embeddings + HITL produces high-trust memory. The
paper_writer is the first consumer that turns that memory into a *new artifact*
rather than answering an ad-hoc query.

## What's already here
- `prompt.md` — the role description that would seed `data/vaults/<scenario>/prompts/paper_writer.v1.md`
- `tools.toml` — declarative allow-list of capabilities the agent can use
- (no `agent.py` yet)

## To enable
1. Add `AgentRole.PAPER_WRITER = "paper_writer"` to `harness/scenario.py`
2. Add a `Scenario(...)` instance in `scenarios/definitions.py` that includes this role
3. Create `agents/paper_writer/agent.py` with a `_build_agent_with_prompt(body)` builder
4. Wire it into `harness/agent_base.py::build_paper_writer()`
5. Add a Streamlit consumer page (e.g. `apps/streamlit/walkthrough/50_paper.py`)

See `agents/extractor/agent.py` or `agents/synthesizer/agent.py` for the
reference shape of an implemented agent.
