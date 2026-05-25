"""Typer CLI — exercises every API surface from the terminal.

Phase 1: vault-stats, ingest are live. Other commands print 'not implemented'
until their phase lands. The full surface is visible at `python -m apps.cli.main --help`
from day one.
"""

from pathlib import Path

import typer

from openacad.runtime.corpus import ingest as ingest_service
from openacad.notes.query import semantic as semantic_service
from openacad.runtime import db
from openacad.notes.persistence import vault as vault_io
app = typer.Typer(
    name="openacad",
    help="Atomic-notes research lifecycle demo. CLI mirror of the FastAPI surface.",
    no_args_is_help=True,
)


# ── Phase 1 ────────────────────────────────────────────────────────────


@app.command("vault-stats")
def vault_stats() -> None:
    """Show counts: atoms, attributes, relations, types, sources, drafts."""
    atoms = vault_io.list_atoms()
    sources = db.list_sources()
    n_chunks = sum(len(db.chunks_for_source(s.id)) for s in sources)
    atoms_emb = len(semantic_service.atoms_store())
    chunks_emb = len(semantic_service.chunks_store())

    typer.echo("── vault ─────────────────────────────────")
    typer.echo(f"  atoms:               {len(atoms)}")
    typer.echo(f"  attribute defs:      {len(vault_io.list_attribute_defs())}")
    typer.echo(f"  relation defs:       {len(vault_io.list_relation_defs())}")
    typer.echo(f"  type defs:           {len(vault_io.list_type_defs())}")
    typer.echo("── data ──────────────────────────────────")
    typer.echo(f"  sources:             {len(sources)}")
    typer.echo(f"  chunks:              {n_chunks}")
    typer.echo(f"  atom embeddings:     {atoms_emb}")
    typer.echo(f"  chunk embeddings:    {chunks_emb}")


@app.command()
def ingest(pdf: Path) -> None:
    """Upload a PDF: parse + chunk + embed chunks + persist."""
    source = ingest_service.ingest_pdf(pdf)
    typer.echo(f"ingested {source.id}: {source.n_pages} pages, {source.n_chunks} chunks")


# ── Phase 2 ────────────────────────────────────────────────────────────


@app.command()
def extract(source_id: str, validate: bool = True, score: bool = True) -> None:
    """Run the 3-stage extraction pipeline on a source (draft → validate → score)."""
    from openacad.notes.intake import from_chunks as extraction_pipeline
    from openacad.runtime import llm as llm

    if not llm.have_api_key():
        typer.echo("LLM_PROVIDER has no API key — set ANTHROPIC_API_KEY / OPENAI_API_KEY first.", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"draft  ← {source_id}")
    drafts = extraction_pipeline.draft(source_id)
    typer.echo(f"  {len(drafts)} drafts produced")
    for d in drafts[:5]:
        typer.echo(f"    {d.draft_id}  {d.type}  {d.suggested_id}")
    if len(drafts) > 5:
        typer.echo(f"    … and {len(drafts) - 5} more")

    if not drafts:
        return

    ids = [d.draft_id for d in drafts]
    if validate:
        typer.echo("validate")
        errs = extraction_pipeline.validate(ids)
        n_clean = sum(1 for v in errs.values() if not v)
        typer.echo(f"  {n_clean}/{len(errs)} drafts pass strict validation")
        for did, errlist in errs.items():
            if errlist:
                typer.echo(f"    {did}: {len(errlist)} error(s)")
                for e in errlist[:3]:
                    typer.echo(f"      - {e}")

    if score:
        typer.echo("score")
        scores = extraction_pipeline.score(ids)
        for did, s in sorted(scores.items(), key=lambda x: -x[1])[:10]:
            typer.echo(f"  {did}: {s:.2f}")


@app.command()
def curate(draft_id: str | None = None, action: str = "accept", reason: str = "") -> None:
    """Curate a draft. action: accept | reject. Use `extract <source-id>` to make drafts."""
    from openacad.notes.curation import _legacy as curate_service
    from openacad.runtime import db
    if draft_id is None:
        typer.echo("pass --draft-id <id>; list with: openacad list-drafts <source-id>", err=True)
        raise typer.Exit(code=1)

    if action == "accept":
        try:
            atom = curate_service.accept(draft_id)
            typer.echo(f"accepted: {atom.metas.id}")
        except ValueError as e:
            typer.echo(f"rejected by validation: {e}", err=True)
            raise typer.Exit(code=1) from e
    elif action == "reject":
        if not reason:
            typer.echo("--reason required for reject", err=True)
            raise typer.Exit(code=1)
        curate_service.reject(draft_id, reason)
        typer.echo(f"rejected: {draft_id}")
    else:
        typer.echo(f"unknown action: {action}", err=True)
        raise typer.Exit(code=1)


@app.command("list-drafts")
def list_drafts(source_id: str) -> None:
    """List pending drafts for a source."""
    from openacad.runtime import db
    drafts = db.drafts_for_source(source_id)
    typer.echo(f"{len(drafts)} pending drafts for {source_id}")
    for d in drafts:
        score = f" score={d.confidence_score:.2f}" if d.confidence_score is not None else ""
        errs = f" errs={len(d.validation_errors)}" if d.validation_errors else ""
        typer.echo(f"  {d.draft_id}  {d.type}  {d.suggested_id}{score}{errs}")


@app.command("accept-all")
def accept_all(source_id: str, min_score: float = 0.0, fix_ids: bool = True) -> None:
    """Demo helper: batch-accept every draft for a source that passes strict validation.

    Real curation is per-draft HITL. This shortcut is for populating the vault fast.

    --min-score filters by confidence_score; 0.0 = take everything that validates.
    --fix-ids auto-suffixes draft suggested_ids if they collide with existing atoms.
    """
    from openacad.notes.curation import _legacy as curate_service
    from openacad.runtime import db
    drafts = db.drafts_for_source(source_id)
    if not drafts:
        typer.echo(f"no drafts for {source_id}")
        return

    n_accepted = n_rejected = n_errored = 0
    for d in drafts:
        if d.confidence_score is not None and d.confidence_score < min_score:
            n_rejected += 1
            continue

        if fix_ids:
            from openacad.notes.persistence import vault as vault_io
            base = d.suggested_id
            suffix = 1
            while vault_io.atom_exists(d.suggested_id):
                d.suggested_id = f"{base}-{suffix}"
                suffix += 1
            if suffix > 1:
                db.upsert_draft(d)

        try:
            atom = curate_service.accept(d.draft_id)
            n_accepted += 1
            typer.echo(f"  ✓ {atom.metas.id}")
        except ValueError as e:
            n_errored += 1
            typer.echo(f"  ✗ {d.draft_id}: {e}", err=True)

    typer.echo(f"── accepted: {n_accepted}  errored: {n_errored}  filtered: {n_rejected} ──")


@app.command("registry-show")
def registry_show(kind: str = "all") -> None:
    """List registry entries. kind: all | attributes | relations | types | proposals."""
    if kind in {"all", "attributes"}:
        typer.echo("── attributes ─────────────────────────────")
        for d in vault_io.list_attribute_defs():
            allowed = f" allowed={d.allowed_values}" if d.allowed_values else ""
            typer.echo(f"  {d.key}  ({d.value_type}{allowed}, used {d.usage_count}x)")
    if kind in {"all", "relations"}:
        typer.echo("── relations ──────────────────────────────")
        for d in vault_io.list_relation_defs():
            inverse = f"  ↔ {d.inverse}" if d.inverse else ""
            typer.echo(f"  {d.key}{inverse}  (used {d.usage_count}x)")
    if kind in {"all", "types"}:
        typer.echo("── types ──────────────────────────────────")
        for d in vault_io.list_type_defs():
            typer.echo(f"  {d.key}  — {d.description}")
    if kind in {"all", "proposals"}:
        from openacad.runtime import db
        proposals = db.list_proposals()
        if proposals:
            typer.echo("── proposals ──────────────────────────────")
            for p in proposals:
                typer.echo(f"  {p.id}  [{p.state}]  {p.kind}: {p.key}")


# ── Phase 3 ────────────────────────────────────────────────────────────


@app.command("notes-search")
def notes_search(
    type: str | None = None,
    tag: str | None = None,
    where: str | None = None,
    keyword: str | None = None,
    semantic: str | None = None,
    limit: int = 20,
) -> None:
    """Filtered atom browse. where format: 'attr.key=value' (e.g. 'evidence.confidence=high')."""
    from openacad.notes.query import hybrid as retrieval
    where_dict = None
    if where:
        if "=" not in where:
            typer.echo("--where format: attr.key=value", err=True)
            raise typer.Exit(code=1)
        k, v = where.split("=", 1)
        where_dict = {k: v}

    result = retrieval.query(
        type=type, where=where_dict, semantic=semantic, keyword=keyword, limit=limit
    )
    typer.echo(f"plan: {' → '.join(result.explain.get('plan', []))}")
    typer.echo(f"counts: {result.explain.get('counts', {})}")
    typer.echo(f"── {len(result.atoms)} atoms ─────────────────────────")
    for a in result.atoms:
        if tag and tag not in a.metas.tags:
            continue
        head = a.content.replace("\n", " ")[:80]
        typer.echo(f"  {a.metas.id}  [{a.metas.type}]")
        typer.echo(f"    {head}…")


@app.command()
def ask(question: str) -> None:
    """Run the tool-calling synthesis agent; print answer + tool trace."""
    from openacad.runtime import llm as llm
    from openacad.agents.synthesizer import agent as synthesis_agent
    from openacad.runtime import db
    if not llm.have_api_key():
        typer.echo("no LLM API key — set ANTHROPIC_API_KEY / OPENAI_API_KEY", err=True)
        raise typer.Exit(code=1)

    result = synthesis_agent.ask(question)
    typer.echo("── answer ─────────────────────────────────")
    typer.echo(result.answer)
    typer.echo("── cited atoms ────────────────────────────")
    for aid in result.cited_atoms:
        typer.echo(f"  {aid}")
    typer.echo("── tool trace ─────────────────────────────")
    for tc_id in result.tool_call_ids:
        tcs = db.list_tool_calls()
        tc = next((t for t in tcs if t.id == tc_id), None)
        if tc:
            typer.echo(f"  {tc.tool_name}({tc.arguments}) → {tc.n_results} results in {tc.latency_ms}ms")
    typer.echo(f"── tokens: in={result.tokens_in} out={result.tokens_out}  latency={result.latency_ms}ms ──")


# ── Phase 4 ────────────────────────────────────────────────────────────


@app.command()
def compare(question: str | None = None, gold: bool = False) -> None:
    """Run B0/B1/A on a question (or the whole gold set with --gold)."""
    from openacad import compare as compare_service
    from openacad.runtime import llm as llm
    import yaml

    if not llm.have_api_key():
        typer.echo("no LLM API key — set ANTHROPIC_API_KEY / OPENAI_API_KEY", err=True)
        raise typer.Exit(code=1)

    if gold:
        from pathlib import Path
        gold_path = Path(__file__).resolve().parent.parent / "data" / "gold" / "questions.yaml"
        qs = yaml.safe_load(gold_path.read_text())
        from openacad.runtime import db
        sources = db.list_sources()
        paper_ids = [s.id for s in sources]
        questions = [q["question"] for q in qs]
        curve = compare_service.amortization_curve(questions, paper_ids)
        typer.echo(f"break-even: A_vs_B0={curve['break_even']['A_vs_B0']} A_vs_B1={curve['break_even']['A_vs_B1']}")
        typer.echo("cumulative tokens:")
        typer.echo(f"  B0: {curve['cumulative_tokens']['B0']}")
        typer.echo(f"  B1: {curve['cumulative_tokens']['B1']}")
        typer.echo(f"  A:  {curve['cumulative_tokens']['A']}")
    elif question:
        out = compare_service.compare_one(question, [])
        for pipe in ("B0", "B1", "A"):
            r = out[pipe]
            typer.echo(f"── {pipe} ────────────────────────")
            typer.echo(f"tokens_in={r.tokens_in}  tokens_out={r.tokens_out}  latency={r.latency_ms}ms  units={r.n_units_retrieved}")
            typer.echo(r.answer[:400])
    else:
        typer.echo("provide --question or --gold", err=True)
        raise typer.Exit(code=1)


@app.command()
def contradictions(domain: str | None = None, weak: bool = False, limit: int = 20) -> None:
    """Mine the graph for contradictions (strong + optionally weak structural)."""
    from openacad import contradictions as contradiction_service
    pairs = contradiction_service.find_contradictions(domain=domain, include_weak=weak, limit=limit)
    typer.echo(f"── {len(pairs)} contradicting pairs ─────────────────")
    for p in pairs:
        typer.echo(f"  [{p['strength']}] {p['a']} ↔ {p['b']}")
        typer.echo(f"    {p['reason']}")


@app.command()
def synthesize(topic: str | None = None, atom_id: list[str] = typer.Option(None, "--atom-id"), style: str = "academic") -> None:
    """Generate a paragraph draft from a topic / atom set, cited from atoms."""
    from openacad.runtime import llm as llm
    from openacad import synthesis as synthesis_service
    if not llm.have_api_key():
        typer.echo("no LLM API key — set ANTHROPIC_API_KEY / OPENAI_API_KEY", err=True)
        raise typer.Exit(code=1)
    result = synthesis_service.synthesize(topic=topic, atom_ids=list(atom_id) if atom_id else None, style=style)
    typer.echo(result.answer)
    typer.echo()
    typer.echo(f"cited: {result.cited_atoms}")


@app.command()
def gaps(confidence: str = "high", domain: str | None = None, limit: int = 20) -> None:
    """Find weak claims (high-confidence claims with no supporting evidence)."""
    from openacad import gaps as gap_service
    out = gap_service.find_gaps(confidence_threshold=confidence, domain=domain, limit=limit)
    typer.echo(f"── {len(out)} gap candidates ────────────────────────")
    for g in out:
        typer.echo(f"  {g['id']}  [{g['type']}, confidence={g['confidence']}]")
        typer.echo(f"    {g['summary'][:100]}…")


@app.command("cross-paper")
def cross_paper(source_a: str, source_b: str | None = None, min_shared: int = 1, limit: int = 20) -> None:
    """Find related atoms across papers."""
    from openacad import cross_paper as cross_paper_service
    pairs = cross_paper_service.find_cross_paper(
        source_a=source_a, source_b=source_b, min_shared_attributes=min_shared, limit=limit
    )
    typer.echo(f"── {len(pairs)} cross-paper links ────────────────────")
    for p in pairs:
        typer.echo(f"  [{p['kind']}] {p['a']} ↔ {p['b']}")
        if p.get("relation"):
            typer.echo(f"    via: {p['relation']}")
        if p.get("shared_attributes"):
            typer.echo(f"    shared: {', '.join(p['shared_attributes'][:3])}")


@app.command("eval-report")
def eval_report() -> None:
    """Print the full eval table + amortization curve."""
    import subprocess, sys
    from pathlib import Path
    script = Path(__file__).resolve().parent.parent / "scripts" / "eval_report.py"
    subprocess.run([sys.executable, str(script)], check=False)


@app.command("prompt-promote")
def prompt_promote(version: str) -> None:
    """Promote a proposed prompt version to active."""
    from openacad import eval_report as eval_service
    try:
        result = eval_service.promote_prompt(version)
        typer.echo(f"promoted: {result}")
    except ValueError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(code=1) from e


@app.command("prompt-regen")
def prompt_regen() -> None:
    """Manually trigger extraction prompt regeneration from recent eval events."""
    from openacad import eval_report as eval_service
    pv = eval_service.regenerate_extraction_prompt()
    if pv is None:
        typer.echo("not enough eval events to regenerate (need ≥ PROMPT_REGEN_THRESHOLD curate actions)")
    else:
        typer.echo(f"proposed: {pv.version}  (parent={pv.parent_version}, state={pv.state})")


if __name__ == "__main__":
    app()
