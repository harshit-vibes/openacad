// TypeScript shapes that mirror the FastAPI response models.
// These are intentionally loose: optional fields and `unknown` escape hatches
// keep the UI resilient when the backend evolves.

export type AtomSummary = {
  id: string;
  type: string;
  status: string;
  domain: string | null;
  evidence: string | null;
  tags: string[];
  n_relations: number;
  n_sources: number;
  updated_at: string;
  body_preview: string;
};

export type Source = {
  document: string;
  chunk: string;
  span: { start: number; end: number };
  page: number | null;
};

export type Relation = {
  type: string;
  target: string;
};

export type AtomFull = AtomSummary & {
  aliases: string[];
  created_at: string;
  body: string;
  attributes: Record<string, unknown>;
  sources: Source[];
  relations: Relation[];
};

export type AtomListResponse = {
  atoms: AtomSummary[];
  total: number;
  limit: number;
  offset: number;
};

export type SearchResponse = {
  query: string;
  results: AtomSummary[];
  count: number;
};

export type OutgoingEdge = {
  relation: string;
  target_id: string;
  atom: AtomSummary | null;
};

export type SourceResponse = {
  atom_id: string;
  text: string | null;
  sources: Source[];
  error?: string;
};

export type RegistryEntry = {
  name: string;
  uses: number;
  n_atoms: number;
  types?: string[];
  inverse?: string | null;
  first_seen: string;
  is_promoted: boolean;
};

export type RegistryResponse = {
  attributes: RegistryEntry[];
  relations: RegistryEntry[];
  promoted_attributes: string[];
  promoted_relations: string[];
};

export type VaultStats = {
  n_atoms: number;
  n_documents: number;
  n_chunk_files: number;
  n_relations: number;
  n_sources: number;
  n_attributes: number;
  n_relation_types: number;
  by_type: Record<string, number>;
  by_status: Record<string, number>;
  by_domain: Record<string, number>;
};

export type AgentRow = {
  name: string;
  description: string;
  model: string;
  tools: string[];
  skills: string[];
  source: "shipped" | "vault" | "proposed";
  has_proposed: boolean;
};

export type AgentDetail = AgentRow & {
  instruction: string;
  proposed: AgentRow & { instruction: string } | null;
  vault_path: string | null;
};

export type AgentDiff = {
  name: string;
  has_proposed: boolean;
  diff: string;
  active: string;
  proposed: string | null;
};

export type Paper = {
  doc_id: string;
  pdf_path: string | null;
  n_chunks: number;
  n_atoms: number;
  has_pdf: boolean;
};

export type PaperDetail = Paper & {
  chunks: Array<{
    id: string;
    doc_id: string;
    page: number;
    char_start: number;
    char_end: number;
    n_chars: number;
    preview: string;
  }>;
  atoms: Array<{
    id: string;
    type: string;
    status: string;
    chunk: string;
    page: number | null;
  }>;
};

export type Draft = {
  doc_id: string;
  draft_name: string;
  draft_id: string;
  type?: string;
  domain?: string | null;
  body_preview: string;
  n_sources?: number;
  parse_error?: string;
};

export type DraftDetail = {
  doc_id: string;
  draft_name: string;
  draft_id?: string;
  type?: string;
  status?: string;
  tags?: string[];
  attributes?: Record<string, unknown>;
  body?: string;
  sources?: Source[];
  source_text?: string | null;
  raw?: string;
  parse_error?: string;
};

export type Observability = {
  n_events: number;
  by_kind: Array<{ kind: string; count: number }>;
  by_agent: Array<{ agent: string; count: number }>;
  by_day: Array<{ day: string; count: number }>;
  latency_histogram: Array<{ bucket: string; count: number }>;
  latency: { n: number; avg_ms: number; max_ms: number };
  cost: { total_usd: number };
  feed: Array<Record<string, unknown>>;
};

export type ComposeRequest = {
  preset: string;
  title: string;
  sections: string[];
  brief: string;
};

export type ComposeResponse = {
  preset: string;
  title: string;
  brief: string;
  sections: Array<{
    heading: string;
    atoms_cited: Array<{ id: string; type: string; body_preview: string }>;
    draft: string;
  }>;
  status: string;
  note: string;
};

export type AssessRequest = {
  text: string;
  top_terms?: number;
};

export type AssessResponse = {
  n_chars: number;
  top_terms: string[];
  findings: Array<{
    term: string;
    n_hits: number;
    atoms: Array<{ id: string; type: string }>;
    coverage: "covered" | "gap";
  }>;
  gaps: Array<{ term: string }>;
  n_atoms_matched: number;
  matched_atoms: string[];
  summary: {
    covered_terms: number;
    gap_terms: number;
    coverage_ratio: number;
  };
  status: string;
  note: string;
};
