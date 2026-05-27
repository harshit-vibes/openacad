"use client";

import { useEffect, useState } from "react";
import { ArrowRight, ArrowLeft, FileText, Quote } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";

import { api } from "@/lib/api";
import type {
  AtomFull,
  AtomSummary,
  OutgoingEdge,
  SourceResponse,
} from "@/lib/types";

export function AtomSheet({
  atomId,
  open,
  onOpenChange,
}: {
  atomId: string | null;
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const [atom, setAtom] = useState<AtomFull | null>(null);
  const [incoming, setIncoming] = useState<AtomSummary[] | null>(null);
  const [outgoing, setOutgoing] = useState<OutgoingEdge[] | null>(null);
  const [source, setSource] = useState<SourceResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!atomId || !open) {
      setAtom(null);
      setIncoming(null);
      setOutgoing(null);
      setSource(null);
      return;
    }
    setLoading(true);
    setError(null);
    Promise.all([
      api.atom(atomId),
      api.incoming(atomId).catch(() => []),
      api.outgoing(atomId).catch(() => []),
      api.source(atomId).catch(() => null),
    ])
      .then(([a, inc, out, src]) => {
        setAtom(a);
        setIncoming(inc as AtomSummary[]);
        setOutgoing(out as OutgoingEdge[]);
        setSource(src);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [atomId, open]);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-2xl overflow-hidden flex flex-col p-0"
      >
        <SheetHeader className="border-b border-border p-6 space-y-2">
          <SheetTitle className="font-mono text-sm break-all">
            {atomId ?? ""}
          </SheetTitle>
          {atom && (
            <SheetDescription className="flex flex-wrap items-center gap-2 text-xs">
              <Badge variant="secondary">{atom.type}</Badge>
              <Badge variant="outline">{atom.status}</Badge>
              {atom.domain && <Badge variant="outline">{atom.domain}</Badge>}
              <span className="text-muted-foreground">
                updated {atom.updated_at?.slice(0, 10)}
              </span>
            </SheetDescription>
          )}
        </SheetHeader>

        <ScrollArea className="flex-1">
          <div className="p-6 space-y-8">
            {loading && (
              <div className="space-y-3">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-5/6" />
              </div>
            )}

            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}

            {atom && (
              <>
                <section>
                  <SectionLabel icon={FileText}>Body</SectionLabel>
                  <p className="text-sm whitespace-pre-wrap leading-relaxed">
                    {atom.body}
                  </p>
                </section>

                {source?.text && (
                  <section>
                    <SectionLabel icon={Quote}>Source quote</SectionLabel>
                    <blockquote className="text-sm text-muted-foreground border-l-2 border-primary/50 pl-4 py-1 whitespace-pre-wrap leading-relaxed font-serif">
                      {source.text}
                    </blockquote>
                    {atom.sources.map((s, i) => (
                      <p
                        key={i}
                        className="text-[11px] text-muted-foreground mt-2 font-mono"
                      >
                        {s.document} · {s.chunk} · span {s.span.start}–
                        {s.span.end}
                        {s.page ? ` · p.${s.page}` : ""}
                      </p>
                    ))}
                  </section>
                )}

                {atom.tags.length > 0 && (
                  <section>
                    <SectionLabel>Tags</SectionLabel>
                    <div className="flex flex-wrap gap-1.5">
                      {atom.tags.map((t) => (
                        <Badge key={t} variant="outline" className="text-xs">
                          {t}
                        </Badge>
                      ))}
                    </div>
                  </section>
                )}

                {Object.keys(atom.attributes).length > 0 && (
                  <section>
                    <SectionLabel>Attributes</SectionLabel>
                    <dl className="text-xs grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5">
                      {Object.entries(atom.attributes).map(([k, v]) => (
                        <div key={k} className="contents">
                          <dt className="text-muted-foreground font-mono">
                            {k}
                          </dt>
                          <dd className="break-all">{JSON.stringify(v)}</dd>
                        </div>
                      ))}
                    </dl>
                  </section>
                )}

                {(outgoing?.length ?? 0) > 0 && (
                  <section>
                    <SectionLabel icon={ArrowRight}>Outgoing edges</SectionLabel>
                    <ul className="space-y-1.5">
                      {outgoing!.map((edge, i) => (
                        <li
                          key={`${edge.relation}-${edge.target_id}-${i}`}
                          className="text-xs flex items-start gap-2"
                        >
                          <Badge variant="secondary" className="text-[10px]">
                            {edge.relation}
                          </Badge>
                          <span className="font-mono text-muted-foreground break-all">
                            {edge.target_id}
                          </span>
                          {edge.atom === null && (
                            <span className="text-[10px] text-destructive">
                              (missing)
                            </span>
                          )}
                        </li>
                      ))}
                    </ul>
                  </section>
                )}

                {(incoming?.length ?? 0) > 0 && (
                  <section>
                    <SectionLabel icon={ArrowLeft}>Incoming edges</SectionLabel>
                    <ul className="space-y-1.5">
                      {incoming!.map((a) => (
                        <li
                          key={a.id}
                          className="text-xs flex items-start gap-2"
                        >
                          <Badge variant="outline" className="text-[10px]">
                            {a.type}
                          </Badge>
                          <span className="font-mono text-muted-foreground break-all">
                            {a.id}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </section>
                )}

                {/* vault_path lives on AgentDetail; not on AtomFull. */}
              </>
            )}
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}

function SectionLabel({
  children,
  icon: Icon,
}: {
  children: React.ReactNode;
  icon?: React.ComponentType<{ className?: string }>;
}) {
  return (
    <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-2 flex items-center gap-1.5">
      {Icon && <Icon className="h-3 w-3" />}
      {children}
    </div>
  );
}
