"use client";

import { useState } from "react";
import { ScanText } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { PageHeader } from "@/components/page-header";

import { api } from "@/lib/api";
import type { AssessResponse } from "@/lib/types";

const SAMPLE = `Climate adaptation in vulnerable regions requires more than emissions cuts.
Migration pressure, food insecurity, and ocean acidification combine to push
several SDG targets out of reach by 2030. National poverty lines need
harmonising before halving extreme poverty becomes meaningful.`;

export default function AssessPage() {
  const [text, setText] = useState(SAMPLE);
  const [result, setResult] = useState<AssessResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const r = await api.assess({ text });
      setResult(r);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="px-6 md:px-10 py-8 max-w-5xl mx-auto">
      <PageHeader
        title="Assess"
        description="Heuristic coverage analyser. Paste a draft, see which atoms back it up and where the gaps are."
      />

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <form onSubmit={onSubmit} className="lg:col-span-2 space-y-4">
          <div className="space-y-2">
            <Label htmlFor="text">Draft / artifact</Label>
            <Textarea
              id="text"
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={14}
              className="text-sm leading-relaxed"
            />
          </div>
          <Button type="submit" disabled={loading} className="w-full">
            <ScanText className="h-4 w-4 mr-1.5" />
            {loading ? "Scanning…" : "Run coverage assessment"}
          </Button>
        </form>

        <div className="lg:col-span-3 space-y-4">
          {error && (
            <Alert variant="destructive">
              <AlertTitle>Assessor failed</AlertTitle>
              <AlertDescription className="font-mono text-xs">
                {error}
              </AlertDescription>
            </Alert>
          )}
          {loading && (
            <Card>
              <CardContent className="space-y-3 py-6">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-full" />
              </CardContent>
            </Card>
          )}
          {result && !loading && (
            <>
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Coverage summary</CardTitle>
                  <CardDescription className="text-xs">
                    {result.summary.covered_terms} of {result.findings.length}{" "}
                    terms matched ({Math.round(result.summary.coverage_ratio * 100)}%)
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="text-xs grid grid-cols-3 gap-3">
                    <Stat
                      label="Atoms matched"
                      value={result.n_atoms_matched}
                    />
                    <Stat
                      label="Coverage gaps"
                      value={result.gaps.length}
                    />
                    <Stat
                      label="Chars scanned"
                      value={result.n_chars}
                    />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Term-by-term findings</CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="text-xs space-y-2">
                    {result.findings.map((f) => (
                      <li
                        key={f.term}
                        className="flex items-start gap-2 border-b border-border/40 pb-2 last:border-0 last:pb-0"
                      >
                        <Badge
                          variant={
                            f.coverage === "covered" ? "secondary" : "outline"
                          }
                          className="text-[10px]"
                        >
                          {f.coverage}
                        </Badge>
                        <div className="flex-1">
                          <div className="font-medium">{f.term}</div>
                          {f.atoms.length > 0 && (
                            <div className="mt-1 text-muted-foreground">
                              {f.atoms
                                .map((a) => a.id)
                                .slice(0, 3)
                                .join(" · ")}
                            </div>
                          )}
                        </div>
                        <span className="tabular-nums text-muted-foreground">
                          {f.n_hits}
                        </span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
              {result.status === "stub" && (
                <p className="text-[11px] text-muted-foreground">
                  {result.note}
                </p>
              )}
            </>
          )}
          {!result && !loading && !error && (
            <Card>
              <CardContent className="py-12 text-center text-sm text-muted-foreground">
                Paste a draft, then run the assessment.
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
        {label}
      </div>
      <div className="text-lg font-semibold tabular-nums">{value}</div>
    </div>
  );
}
