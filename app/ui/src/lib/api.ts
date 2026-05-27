// Typed thin client over the openacad FastAPI playground surface.
//
// All Server Components fetch through these helpers so request shapes
// stay consistent. We disable Next's request cache by default (the data
// changes whenever the vault changes) and rely on the SQLite-backed
// backend being fast enough for fresh reads.

import type {
  AgentDetail,
  AgentDiff,
  AgentRow,
  AssessRequest,
  AssessResponse,
  AtomFull,
  AtomListResponse,
  ComposeRequest,
  ComposeResponse,
  Draft,
  DraftDetail,
  Observability,
  OutgoingEdge,
  Paper,
  PaperDetail,
  RegistryResponse,
  SearchResponse,
  SourceResponse,
  VaultStats,
  AtomSummary,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type FetchInit = RequestInit & { next?: { revalidate?: number } };

async function request<T>(
  path: string,
  init: FetchInit = { cache: "no-store" },
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${path}\n${body}`);
  }
  return (await res.json()) as T;
}

function qs(params: Record<string, string | number | undefined | null>) {
  const out = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    out.set(k, String(v));
  }
  const s = out.toString();
  return s ? `?${s}` : "";
}

export const api = {
  // vault
  stats: () => request<VaultStats>("/vault/stats"),
  atoms: (params: {
    type?: string;
    domain?: string;
    status?: string;
    q?: string;
    limit?: number;
    offset?: number;
  } = {}) => request<AtomListResponse>(`/vault/atoms${qs(params)}`),
  atom: (id: string) => request<AtomFull>(`/vault/atoms/${encodeURIComponent(id)}`),
  incoming: (id: string) =>
    request<AtomSummary[]>(`/vault/atoms/${encodeURIComponent(id)}/incoming`),
  outgoing: (id: string) =>
    request<OutgoingEdge[]>(`/vault/atoms/${encodeURIComponent(id)}/outgoing`),
  source: (id: string) =>
    request<SourceResponse>(`/vault/atoms/${encodeURIComponent(id)}/source`),
  search: (q: string, top_k = 10) =>
    request<SearchResponse>(`/vault/search${qs({ q, top_k })}`),
  semantic: (q: string, top_k = 10) =>
    request<SearchResponse>(`/vault/semantic${qs({ q, top_k })}`),
  registry: () => request<RegistryResponse>("/vault/registry"),

  // agents
  agents: () => request<{ agents: AgentRow[]; count: number }>("/agents"),
  agent: (name: string) =>
    request<AgentDetail>(`/agents/${encodeURIComponent(name)}`),
  agentDiff: (name: string) =>
    request<AgentDiff>(`/agents/${encodeURIComponent(name)}/diff`),

  // ingest
  papers: () =>
    request<{ papers: Paper[]; count: number }>("/ingest/papers"),
  paper: (id: string) =>
    request<PaperDetail>(`/ingest/papers/${encodeURIComponent(id)}`),
  ingestStats: () =>
    request<{ n_papers: number; n_chunks: number; n_atoms_derived: number }>(
      "/ingest/stats",
    ),

  // curate
  drafts: () =>
    request<{ drafts: Draft[]; count: number }>("/curate/drafts"),
  docDrafts: (doc_id: string) =>
    request<{ doc_id: string; drafts: Draft[]; count: number }>(
      `/curate/drafts/${encodeURIComponent(doc_id)}`,
    ),
  draft: (doc_id: string, draft_name: string) =>
    request<DraftDetail>(
      `/curate/drafts/${encodeURIComponent(doc_id)}/${encodeURIComponent(draft_name)}`,
    ),

  // observability
  observability: () =>
    request<Observability>("/projections/observability"),

  // mutations — use no caching, POST JSON
  compose: (req: ComposeRequest) =>
    request<ComposeResponse>("/compose", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(req),
      cache: "no-store",
    }),
  assess: (req: AssessRequest) =>
    request<AssessResponse>("/assess", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(req),
      cache: "no-store",
    }),
};
