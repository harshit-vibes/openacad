"use client";

import { useState } from "react";
import { Sparkles } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { PageHeader } from "@/components/page-header";

import { api } from "@/lib/api";
import type { ComposeResponse } from "@/lib/types";

const PRESETS = ["brief", "paper", "book"];

export default function ComposePage() {
  const [preset, setPreset] = useState("brief");
  const [title, setTitle] = useState("Climate progress under the SDGs");
  const [sections, setSections] = useState(
    "Background\nKey findings\nGaps\nRecommendations",
  );
  const [brief, setBrief] = useState("");
  const [result, setResult] = useState<ComposeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const out = await api.compose({
        preset,
        title,
        sections: sections.split("\n").map((s) => s.trim()).filter(Boolean),
        brief,
      });
      setResult(out);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="px-6 md:px-10 py-8 max-w-5xl mx-auto">
      <PageHeader
        title="Compose"
        description="Stitch vault atoms into a brief, paper, or book chapter. Stub mode wires FTS hits into each section."
      />

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <form onSubmit={onSubmit} className="lg:col-span-2 space-y-4">
          <div className="space-y-2">
            <Label>Preset</Label>
            <div className="flex gap-2">
              {PRESETS.map((p) => (
                <Button
                  key={p}
                  type="button"
                  variant={preset === p ? "default" : "outline"}
                  size="sm"
                  onClick={() => setPreset(p)}
                >
                  {p}
                </Button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="title">Title</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="sections">Sections (one per line)</Label>
            <Textarea
              id="sections"
              value={sections}
              onChange={(e) => setSections(e.target.value)}
              rows={6}
              className="font-mono text-xs"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="brief">Brief / outline</Label>
            <Textarea
              id="brief"
              value={brief}
              onChange={(e) => setBrief(e.target.value)}
              rows={4}
              placeholder="Optional context for the composer"
            />
          </div>

          <Button type="submit" disabled={loading} className="w-full">
            <Sparkles className="h-4 w-4 mr-1.5" />
            {loading ? "Composing…" : "Compose"}
          </Button>
        </form>

        <div className="lg:col-span-3">
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertTitle>Composer failed</AlertTitle>
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
                <Skeleton className="h-4 w-5/6" />
              </CardContent>
            </Card>
          )}
          {result && !loading && (
            <div className="space-y-4">
              {result.status === "stub" && (
                <Badge variant="outline" className="text-[10px]">
                  stub mode · {result.note}
                </Badge>
              )}
              {result.sections.map((s, i) => (
                <Card key={i}>
                  <CardHeader>
                    <CardTitle className="text-sm">{s.heading}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <pre className="text-xs whitespace-pre-wrap font-mono bg-muted/30 rounded p-3 mb-3">
                      {s.draft}
                    </pre>
                    {s.atoms_cited.length > 0 && (
                      <div>
                        <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-1.5">
                          Citations
                        </div>
                        <ul className="text-xs space-y-1.5">
                          {s.atoms_cited.map((a) => (
                            <li key={a.id} className="flex gap-2 items-start">
                              <Badge
                                variant="outline"
                                className="text-[10px] py-0"
                              >
                                {a.type}
                              </Badge>
                              <span className="font-mono text-muted-foreground break-all">
                                {a.id}
                              </span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
          {!result && !loading && !error && (
            <Card>
              <CardContent className="py-12 text-center text-sm text-muted-foreground">
                Fill the form and hit{" "}
                <span className="font-medium">Compose</span> to draft an
                artifact from vault atoms.
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
