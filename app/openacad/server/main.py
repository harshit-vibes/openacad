"""FastAPI entrypoint for the openacad playground UI.

Boots a small surface backed by the M1+M2 ``Vault`` library:

- ``/vault/...``   — atoms, search, source-text, registry, stats
- ``/agents/...``  — list / show / diff shipped + vault-customised agents
- ``/ingest/...``  — paper library view (documents + chunks)
- ``/compose``     — stub composer endpoint
- ``/assess``      — stub coverage-assessment endpoint
- ``/projections/observability`` — KPI rollups built from activity.jsonl
- ``/curate/...``  — read-only mirror of draft proposals

Legacy routers from the prior thesis demo are imported defensively: if their
imports break (renamed modules during M1), we skip them and continue. The new
playground surface is what the Next.js UI consumes.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


# ---------------------------------------------------------------------------
# Defensive legacy-router imports — wrap each so a broken legacy module never
# breaks server boot. Anything that fails to import is silently skipped.
# ---------------------------------------------------------------------------

_LEGACY_ROUTERS: list[tuple[str, str, str]] = []  # (attr, prefix, tag)


def _try_legacy(module_name: str, prefix: str, tag: str) -> None:
    """Best-effort import of a legacy router module."""
    try:
        import importlib

        mod = importlib.import_module(f"openacad.server.routers.{module_name}")
        router = getattr(mod, "router", None)
        if router is not None:
            _LEGACY_ROUTERS.append((module_name, prefix, tag))
            _LEGACY_ROUTER_OBJS[module_name] = router
    except Exception:  # noqa: BLE001 — legacy modules may have stale imports
        pass


_LEGACY_ROUTER_OBJS: dict[str, object] = {}

for _name, _prefix, _tag in [
    ("sources", "/sources", "sources"),
    ("extract", "/extract", "extract"),
    ("curate", "/curate-legacy", "curate-legacy"),
    ("registry", "/registry-legacy", "registry-legacy"),
    ("notes", "/notes", "notes"),
    ("query", "/query", "query"),
    ("compare", "/compare", "compare"),
    ("contradictions", "/contradictions", "lifecycle"),
    ("synthesize", "/synthesize", "lifecycle"),
    ("gaps", "/gaps", "lifecycle"),
    ("cross_paper", "/cross-paper", "lifecycle"),
    ("evals", "/evals", "evals"),
]:
    _try_legacy(_name, _prefix, _tag)


# ---------------------------------------------------------------------------
# New playground routers (M4).
# ---------------------------------------------------------------------------

from openacad.server.routers import (  # noqa: E402
    agents_routes,
    assess_routes,
    compose_routes,
    curate_routes,
    ingest_routes,
    projections_routes,
    vault_routes,
)


# ---------------------------------------------------------------------------
# CORS — allow the Next.js dev server at :3000.
# ---------------------------------------------------------------------------

try:
    from openacad.runtime.settings import settings as _settings

    _ALLOWED_ORIGINS = list(getattr(_settings, "cors_origins", []) or [])
except Exception:  # noqa: BLE001
    _ALLOWED_ORIGINS = []

if not _ALLOWED_ORIGINS:
    _ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # The Vault dependency is lazy-loaded on first request (see
    # openacad.server.deps). No eager work at boot.
    yield


app = FastAPI(
    title="openacad playground API",
    description=(
        "Backend for the openacad Next.js playground. Atoms, agents, ingest, "
        "compose, assess, observability — all backed by the markdown vault."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.get("/", tags=["meta"])
def root() -> dict:
    return {
        "name": "openacad-playground",
        "version": "0.1.0",
        "docs": "/docs",
        "ui": "http://localhost:3000",
    }


@app.get("/healthz", tags=["meta"])
def healthz() -> dict:
    return {"ok": True}


# New playground routers — register first so they shadow any legacy collisions.
app.include_router(vault_routes.router, prefix="/vault", tags=["vault"])
app.include_router(agents_routes.router, prefix="/agents", tags=["agents"])
app.include_router(ingest_routes.router, prefix="/ingest", tags=["ingest"])
app.include_router(compose_routes.router, prefix="/compose", tags=["compose"])
app.include_router(assess_routes.router, prefix="/assess", tags=["assess"])
app.include_router(curate_routes.router, prefix="/curate", tags=["curate"])
app.include_router(
    projections_routes.router, prefix="/projections", tags=["projections"]
)


# Then mount whatever legacy routers managed to import — useful for the
# thesis demo / `/docs` browsing but not relied on by the new UI.
for _name, _prefix, _tag in _LEGACY_ROUTERS:
    _router = _LEGACY_ROUTER_OBJS.get(_name)
    if _router is not None:
        try:
            app.include_router(_router, prefix=_prefix, tags=[_tag])
        except Exception:  # noqa: BLE001
            # Some legacy routers may collide with the new surface — skip.
            pass
