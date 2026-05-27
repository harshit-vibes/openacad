import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";

const RUNGS = [
  {
    n: 1,
    name: "Raw PDF, no chunks",
    summary:
      "Drop the entire paper into the prompt. The model invents details, citations are non-verifiable.",
    cost: "$$$$",
    quality: "0.30",
  },
  {
    n: 2,
    name: "Chunk RAG",
    summary:
      "Naive chunk retrieval. Better fidelity but answers still drift between chunks; no cross-paper synthesis.",
    cost: "$$$",
    quality: "0.45",
  },
  {
    n: 3,
    name: "Chunks + structured frontmatter",
    summary:
      "Add YAML metadata; the retrieval can now filter, but the model still produces glue prose with no grounding.",
    cost: "$$$",
    quality: "0.55",
  },
  {
    n: 4,
    name: "Atomic notes (no curation)",
    summary:
      "Decompose claims into atoms with source spans. Answers cite atoms now, but extractor errors propagate unchecked.",
    cost: "$$",
    quality: "0.65",
  },
  {
    n: 5,
    name: "Atoms + scholar HITL",
    summary:
      "A human accepts / edits / rejects each atom. Quality jumps; cost stays bounded because rejects are cheap.",
    cost: "$$",
    quality: "0.78",
  },
  {
    n: 6,
    name: "Atoms + registry validation",
    summary:
      "Attribute and relation schema auto-promote. Typos and orphan keys surface immediately.",
    cost: "$",
    quality: "0.82",
  },
  {
    n: 7,
    name: "Deterministic tool calls",
    summary:
      "The agent uses search/source-text/traverse_relations instead of generating cited content. Source-grounded by construction.",
    cost: "$",
    quality: "0.88",
  },
  {
    n: 8,
    name: "Split + merge invariants",
    summary:
      "Atoms can be refined without losing provenance. Source spans stay sound across the lifecycle.",
    cost: "$",
    quality: "0.91",
  },
  {
    n: 9,
    name: "Agentic architecture (this product)",
    summary:
      "Agents, skills, tools as first-class .md + Python. Markdown-on-disk vault. Obsidian-compatible. This page lives in the next rung — you're already here.",
    cost: "$",
    quality: "0.95",
  },
];

export default function MuseumPage() {
  return (
    <div className="px-6 md:px-10 py-8 max-w-5xl mx-auto">
      <PageHeader
        title="The 9-rung thesis"
        description="How openacad climbed from raw-PDF RAG to a verifiable, agent-driven vault. The Streamlit demo is frozen at /museum/streamlit and tagged thesis-v1."
      />

      <div className="space-y-4">
        {RUNGS.map((r) => (
          <Card key={r.n}>
            <CardHeader>
              <div className="flex items-start justify-between gap-3 flex-wrap">
                <CardTitle className="text-sm flex items-center gap-2">
                  <span className="h-6 w-6 rounded-full bg-primary/10 flex items-center justify-center text-[11px] font-mono text-primary">
                    {r.n}
                  </span>
                  {r.name}
                </CardTitle>
                <div className="flex gap-2 text-[10px]">
                  <Badge variant="outline">cost {r.cost}</Badge>
                  <Badge variant="secondary">q {r.quality}</Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {r.summary}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      <p className="text-[11px] text-muted-foreground mt-10">
        The frozen rung-by-rung Streamlit walkthrough still works:{" "}
        <code className="bg-muted/40 px-1 py-0.5 rounded">openacad museum</code>.
      </p>
    </div>
  );
}
