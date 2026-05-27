import { ClipboardCheck } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PageHeader } from "@/components/page-header";

import { api } from "@/lib/api";

export default async function CuratePage() {
  let drafts: Awaited<ReturnType<typeof api.drafts>> | null = null;
  let error: string | null = null;
  try {
    drafts = await api.drafts();
  } catch (e) {
    error = String(e);
  }

  // Group by doc_id.
  type Drafts = NonNullable<typeof drafts>["drafts"];
  const byDoc = new Map<string, Drafts>();
  if (drafts) {
    for (const d of drafts.drafts) {
      const arr = byDoc.get(d.doc_id) ?? [];
      arr.push(d);
      byDoc.set(d.doc_id, arr);
    }
  }

  return (
    <div className="px-6 md:px-10 py-8 max-w-6xl mx-auto">
      <PageHeader
        title="Curate"
        description="Drafts queued for the scholar. This view is read-only — accept / edit / reject verdicts live in the CLI."
        kpis={
          drafts
            ? [{ label: "Pending drafts", value: drafts.count }]
            : undefined
        }
      />

      <Alert className="mb-6">
        <ClipboardCheck className="h-4 w-4" />
        <AlertTitle>Read-only by design</AlertTitle>
        <AlertDescription className="text-xs">
          Use{" "}
          <code className="bg-muted/50 px-1 py-0.5 rounded">
            openacad curate
          </code>{" "}
          to apply verdicts; every action is logged to{" "}
          <code className="bg-muted/50 px-1 py-0.5 rounded">
            .openacad/activity.jsonl
          </code>
          .
        </AlertDescription>
      </Alert>

      {error && (
        <div className="text-sm text-destructive">API error: {error}</div>
      )}

      {byDoc.size === 0 && !error && (
        <Card>
          <CardContent className="py-16 text-center text-sm text-muted-foreground">
            No drafts pending. Run{" "}
            <code className="bg-muted/50 px-1 py-0.5 rounded">
              openacad extract &lt;doc&gt;
            </code>{" "}
            to generate some.
          </CardContent>
        </Card>
      )}

      <div className="space-y-6">
        {[...byDoc.entries()].map(([docId, items]) => (
          <Card key={docId}>
            <CardHeader>
              <CardTitle className="text-sm font-mono">{docId}</CardTitle>
              <CardDescription className="text-xs">
                {items.length} pending draft{items.length === 1 ? "" : "s"}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {items.map((d) => (
                <div
                  key={d.draft_id}
                  className="rounded-md border border-border p-3"
                >
                  <div className="flex items-start gap-2 mb-2">
                    {d.type && (
                      <Badge variant="secondary" className="text-[10px]">
                        {d.type}
                      </Badge>
                    )}
                    {d.domain && (
                      <Badge variant="outline" className="text-[10px]">
                        {d.domain}
                      </Badge>
                    )}
                    <span className="font-mono text-[11px] text-muted-foreground ml-auto">
                      {d.draft_name}
                    </span>
                  </div>
                  <p className="text-xs leading-relaxed">{d.body_preview}</p>
                  {d.parse_error && (
                    <p className="text-[11px] text-destructive mt-2 font-mono">
                      parse error: {d.parse_error}
                    </p>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
