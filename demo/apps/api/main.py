"""FastAPI entrypoint. Boot-time: load Schema, build NetworkX graph, load embeddings.

Phase 1: skeleton + sources router live. Other routers are stubs returning 501 until
their phase lands. The full surface is visible at /docs from day one.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from openacad.runtime.settings import settings
from apps.api.routers import (
    compare,
    contradictions,
    cross_paper,
    curate,
    evals,
    extract,
    gaps,
    notes,
    query,
    registry,
    sources,
    synthesize,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Phase 2+: load Schema from vault/registry, rebuild NetworkX from vault/notes,
    # warm embedding model. Stubbed for Phase 1.
    yield


app = FastAPI(
    title="openacad demo API",
    description=(
        "Atomic-notes research lifecycle demo. Tier-A AI assistance over a curated, "
        "registry-governed vault. See /docs for the full surface."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["meta"])
def root() -> dict:
    return {
        "name": "openacad-demo",
        "version": "0.1.0",
        "thesis": "atomic notes + HITL + deterministic tool calls > raw-PDF RAG",
        "docs": "/docs",
    }


# Routers — registered in the order Phase 1→4 brings them online.
app.include_router(sources.router, prefix="/sources", tags=["sources"])
app.include_router(extract.router, prefix="/extract", tags=["extract"])
app.include_router(curate.router, prefix="/curate", tags=["curate"])
app.include_router(registry.router, prefix="/registry", tags=["registry"])
app.include_router(notes.router, prefix="/notes", tags=["notes"])
app.include_router(query.router, prefix="/query", tags=["query"])
app.include_router(compare.router, prefix="/compare", tags=["compare"])
app.include_router(contradictions.router, prefix="/contradictions", tags=["lifecycle"])
app.include_router(synthesize.router, prefix="/synthesize", tags=["lifecycle"])
app.include_router(gaps.router, prefix="/gaps", tags=["lifecycle"])
app.include_router(cross_paper.router, prefix="/cross-paper", tags=["lifecycle"])
app.include_router(evals.router, prefix="/evals", tags=["evals"])
