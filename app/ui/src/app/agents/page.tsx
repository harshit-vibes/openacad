import Link from "next/link";

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

export default async function AgentsPage() {
  let agents: Awaited<ReturnType<typeof api.agents>> | null = null;
  let error: string | null = null;
  try {
    agents = await api.agents();
  } catch (e) {
    error = String(e);
  }

  return (
    <div className="px-6 md:px-10 py-8 max-w-6xl mx-auto">
      <PageHeader
        title="Agents"
        description="Claude Code-format .md files. Frontmatter declares the model, tools, skills. Body is the system prompt."
        kpis={
          agents
            ? [{ label: "Shipped + vault", value: agents.count }]
            : undefined
        }
      />

      {error && (
        <div className="my-4 text-sm text-destructive">API error: {error}</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {agents?.agents.map((a) => (
          <Link key={a.name} href={`/agents/${a.name}`} className="block group">
            <Card className="h-full transition-colors group-hover:border-primary/40">
              <CardHeader>
                <div className="flex items-start justify-between gap-2">
                  <CardTitle className="text-base font-mono">
                    {a.name}
                  </CardTitle>
                  <div className="flex gap-1.5">
                    <Badge
                      variant={a.source === "vault" ? "default" : "secondary"}
                      className="text-[10px]"
                    >
                      {a.source}
                    </Badge>
                    {a.has_proposed && (
                      <Badge variant="outline" className="text-[10px]">
                        proposed
                      </Badge>
                    )}
                  </div>
                </div>
                <CardDescription className="text-sm">
                  {a.description}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-xs">
                <div>
                  <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-1">
                    Model
                  </div>
                  <code className="text-xs">{a.model}</code>
                </div>
                <div>
                  <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-1">
                    Tools
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {a.tools.map((t) => (
                      <Badge
                        key={t}
                        variant="outline"
                        className="text-[10px] py-0"
                      >
                        {t}
                      </Badge>
                    ))}
                    {a.tools.length === 0 && (
                      <span className="text-muted-foreground">none</span>
                    )}
                  </div>
                </div>
                {a.skills.length > 0 && (
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-1">
                      Skills
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {a.skills.map((s) => (
                        <Badge
                          key={s}
                          variant="secondary"
                          className="text-[10px] py-0"
                        >
                          {s}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
