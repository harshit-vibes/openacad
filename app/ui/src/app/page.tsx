import Link from "next/link";
import {
  Atom,
  Bot,
  ClipboardCheck,
  FileText,
  Library,
  LineChart,
  PenSquare,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const CAPABILITIES = [
  {
    icon: Atom,
    title: "Atomic notes you can verify",
    body: "Every atom is a markdown file on disk with a source span you can re-read. Wiki-links resolve, frontmatter is open-vocab.",
    href: "/vault",
    cta: "Browse the vault",
  },
  {
    icon: Bot,
    title: "Agents you can read",
    body: "Four shipped agents — extractor, answerer, scorer, meta-evaluator — defined in Claude Code-format markdown. Swap, version, diff.",
    href: "/agents",
    cta: "Inspect agents",
  },
  {
    icon: Library,
    title: "Ingest and chunk",
    body: "Drop a PDF in, get chunks with character offsets that atoms cite by exact substring. No silent normalization.",
    href: "/ingest",
    cta: "See paper library",
  },
  {
    icon: ClipboardCheck,
    title: "Human in the loop",
    body: "Drafts queue under .openacad/drafts/. Accept, edit, reject, split, merge — every verdict is logged.",
    href: "/curate",
    cta: "View pending drafts",
  },
  {
    icon: PenSquare,
    title: "Compose with citations",
    body: "Stitch atoms into briefs, papers, or longer artifacts. Every claim points back to a chunk and a span.",
    href: "/compose",
    cta: "Open composer",
  },
  {
    icon: LineChart,
    title: "Observable end-to-end",
    body: "Activity log, latency buckets, cost rollups — all from a single .openacad/activity.jsonl. No hidden state.",
    href: "/observability",
    cta: "Open dashboard",
  },
];

export default function Welcome() {
  return (
    <div className="px-6 md:px-10 py-10 max-w-6xl mx-auto">
      <header className="mb-12">
        <Badge variant="outline" className="mb-4 gap-1.5">
          <FileText className="h-3 w-3" />
          100% local · markdown-on-disk
        </Badge>
        <h1 className="text-4xl md:text-5xl font-semibold tracking-tight mb-4 max-w-3xl">
          AI-first notes for scholars.
        </h1>
        <p className="text-lg text-muted-foreground max-w-2xl mb-8">
          Plain markdown atoms with source spans you can verify. Agents you can
          read, edit, version, and swap. Obsidian-compatible — open the vault
          in any editor.
        </p>
        <div className="flex gap-3 flex-wrap">
          <Link href="/vault" className={buttonVariants()}>
            Browse the vault
          </Link>
          <Link
            href="/agents"
            className={buttonVariants({ variant: "outline" })}
          >
            Read the agents
          </Link>
          <Link
            href="/museum"
            className={buttonVariants({ variant: "ghost" })}
          >
            9-rung thesis tour
          </Link>
        </div>
      </header>

      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {CAPABILITIES.map(({ icon: Icon, title, body, href, cta }) => (
          <Link key={href} href={href} className="block group">
            <Card className="h-full transition-colors group-hover:border-primary/40">
              <CardHeader className="space-y-3">
                <div className="h-9 w-9 rounded-md bg-primary/10 flex items-center justify-center">
                  <Icon className="h-4 w-4 text-primary" />
                </div>
                <CardTitle className="text-base font-medium">{title}</CardTitle>
                <CardDescription className="text-sm leading-relaxed">
                  {body}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <span className="text-xs font-medium text-primary group-hover:underline">
                  {cta} →
                </span>
              </CardContent>
            </Card>
          </Link>
        ))}
      </section>

      <section className="mt-16 border-t border-border pt-10">
        <h2 className="text-sm uppercase tracking-wider text-muted-foreground mb-3">
          Pipeline
        </h2>
        <ol className="grid grid-cols-1 md:grid-cols-5 gap-3 text-sm">
          {[
            "Ingest PDF",
            "Chunk text",
            "Extract drafts",
            "Curate atoms",
            "Compose / Ask",
          ].map((step, i) => (
            <li
              key={step}
              className="rounded-lg border border-border p-4 bg-card/40"
            >
              <div className="text-xs text-muted-foreground mb-1">
                Step {i + 1}
              </div>
              <div className="font-medium">{step}</div>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
