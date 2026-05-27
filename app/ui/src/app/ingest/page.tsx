import { FileText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { PageHeader } from "@/components/page-header";

import { api } from "@/lib/api";

export default async function IngestPage() {
  const [papers, stats] = await Promise.all([
    api.papers().catch(() => ({ papers: [], count: 0 })),
    api.ingestStats().catch(() => null),
  ]);

  return (
    <div className="px-6 md:px-10 py-8 max-w-6xl mx-auto">
      <PageHeader
        title="Ingest"
        description="Documents and chunks under .openacad/. Drop a PDF in, openacad chunks it, atoms reference exact spans."
        kpis={
          stats
            ? [
                { label: "Papers", value: stats.n_papers },
                { label: "Chunks", value: stats.n_chunks },
                { label: "Atoms derived", value: stats.n_atoms_derived },
              ]
            : undefined
        }
      />

      <div className="rounded-md border border-border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[50%]">Document</TableHead>
              <TableHead className="text-right">Chunks</TableHead>
              <TableHead className="text-right">Atoms</TableHead>
              <TableHead>Source</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {papers.papers.map((p) => (
              <TableRow key={p.doc_id}>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <FileText className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="font-mono text-xs">{p.doc_id}</span>
                  </div>
                </TableCell>
                <TableCell className="text-right text-xs tabular-nums">
                  {p.n_chunks}
                </TableCell>
                <TableCell className="text-right text-xs tabular-nums">
                  {p.n_atoms}
                </TableCell>
                <TableCell>
                  <Badge
                    variant={p.has_pdf ? "secondary" : "outline"}
                    className="text-[10px]"
                  >
                    {p.has_pdf ? "pdf" : "chunks-only"}
                  </Badge>
                </TableCell>
              </TableRow>
            ))}
            {papers.papers.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={4}
                  className="text-sm text-muted-foreground text-center py-12"
                >
                  No documents ingested yet. Try{" "}
                  <code className="bg-muted px-1 py-0.5 rounded">
                    openacad ingest path/to.pdf
                  </code>
                  .
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
