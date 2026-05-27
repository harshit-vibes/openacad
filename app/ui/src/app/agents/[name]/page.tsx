import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { PageHeader } from "@/components/page-header";

import { api } from "@/lib/api";

export default async function AgentPage({
  params,
}: {
  params: Promise<{ name: string }>;
}) {
  const { name } = await params;
  let agent: Awaited<ReturnType<typeof api.agent>> | null = null;
  let diff: Awaited<ReturnType<typeof api.agentDiff>> | null = null;
  let error: string | null = null;
  try {
    [agent, diff] = await Promise.all([
      api.agent(name),
      api.agentDiff(name).catch(() => null),
    ]);
  } catch (e) {
    error = String(e);
  }

  return (
    <div className="px-6 md:px-10 py-8 max-w-5xl mx-auto">
      <Link
        href="/agents"
        className={`${buttonVariants({ variant: "ghost", size: "sm" })} mb-4`}
      >
        <ArrowLeft className="h-3 w-3 mr-1" /> All agents
      </Link>

      <PageHeader
        title={name}
        description={agent?.description ?? "Agent specification"}
      />

      {error && (
        <div className="text-sm text-destructive">API error: {error}</div>
      )}

      {agent && (
        <div className="space-y-6">
          <div className="flex flex-wrap gap-2 text-xs">
            <Badge variant={agent.source === "vault" ? "default" : "secondary"}>
              source: {agent.source}
            </Badge>
            <Badge variant="outline">model: {agent.model}</Badge>
            {agent.has_proposed && (
              <Badge variant="outline">has proposed</Badge>
            )}
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Tools & skills</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-xs">
              <div>
                <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-1.5">
                  Tools
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {agent.tools.map((t) => (
                    <Badge key={t} variant="outline">
                      {t}
                    </Badge>
                  ))}
                </div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-1.5">
                  Skills
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {agent.skills.length > 0 ? (
                    agent.skills.map((s) => (
                      <Badge key={s} variant="secondary">
                        {s}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-muted-foreground">no skills</span>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Instruction (system prompt)</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="text-xs whitespace-pre-wrap font-mono leading-relaxed bg-muted/30 rounded-md p-4">
                {agent.instruction || "(empty)"}
              </pre>
            </CardContent>
          </Card>

          {diff?.has_proposed && (
            <>
              <Separator />
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Pending proposal — diff</CardTitle>
                </CardHeader>
                <CardContent>
                  <pre className="text-[11px] whitespace-pre-wrap font-mono bg-muted/30 rounded-md p-4 overflow-x-auto">
                    {diff.diff || "(no diff)"}
                  </pre>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      )}
    </div>
  );
}
