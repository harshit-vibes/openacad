import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/page-header";

import { api } from "@/lib/api";

import { LatencyChart } from "./latency-chart";

export default async function ObservabilityPage() {
  let data: Awaited<ReturnType<typeof api.observability>> | null = null;
  let error: string | null = null;
  try {
    data = await api.observability();
  } catch (e) {
    error = String(e);
  }

  return (
    <div className="px-6 md:px-10 py-8 max-w-6xl mx-auto">
      <PageHeader
        title="Observability"
        description="Every agent + vault event logged to .openacad/activity.jsonl. No hidden state."
        kpis={
          data
            ? [
                { label: "Events", value: data.n_events.toLocaleString() },
                {
                  label: "Avg latency",
                  value: data.latency.avg_ms
                    ? `${data.latency.avg_ms}ms`
                    : "—",
                },
                {
                  label: "Total cost",
                  value:
                    data.cost.total_usd > 0
                      ? `$${data.cost.total_usd.toFixed(4)}`
                      : "$0",
                },
              ]
            : undefined
        }
      />

      {error && (
        <div className="text-sm text-destructive">API error: {error}</div>
      )}

      {data && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Latency histogram</CardTitle>
              <CardDescription className="text-xs">
                {data.latency.n} timed events
              </CardDescription>
            </CardHeader>
            <CardContent>
              {data.latency.n > 0 ? (
                <LatencyChart data={data.latency_histogram} />
              ) : (
                <p className="text-xs text-muted-foreground py-12 text-center">
                  No latency data yet. Agent runs will populate this once the
                  runtime starts emitting timings.
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Events by kind</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="text-xs space-y-2">
                {data.by_kind.map((k) => (
                  <li
                    key={k.kind}
                    className="flex items-center justify-between"
                  >
                    <span className="font-mono">{k.kind}</span>
                    <span className="tabular-nums text-muted-foreground">
                      {k.count.toLocaleString()}
                    </span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Events by day</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="text-xs space-y-1.5">
                {data.by_day.map((d) => (
                  <li
                    key={d.day}
                    className="flex items-center justify-between"
                  >
                    <span className="font-mono">{d.day}</span>
                    <span className="tabular-nums text-muted-foreground">
                      {d.count}
                    </span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Events by agent</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="text-xs space-y-1.5">
                {data.by_agent.length === 0 && (
                  <li className="text-muted-foreground">No agent-tagged events yet.</li>
                )}
                {data.by_agent.map((a) => (
                  <li
                    key={a.agent}
                    className="flex items-center justify-between"
                  >
                    <span className="font-mono">{a.agent}</span>
                    <span className="tabular-nums text-muted-foreground">
                      {a.count}
                    </span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="text-sm">Activity feed</CardTitle>
              <CardDescription className="text-xs">
                Most recent first — direct from activity.jsonl
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="text-xs space-y-2 max-h-96 overflow-y-auto">
                {data.feed.slice(0, 50).map((e, i) => {
                  const kind = String(e.kind ?? e.event ?? "event");
                  return (
                    <li
                      key={i}
                      className="border-b border-border/40 pb-2 last:border-0 last:pb-0 flex items-start gap-2"
                    >
                      <Badge variant="outline" className="text-[10px] mt-0.5">
                        {kind}
                      </Badge>
                      <pre className="font-mono text-[11px] flex-1 break-all whitespace-pre-wrap">
                        {JSON.stringify(e, null, 0)}
                      </pre>
                    </li>
                  );
                })}
              </ul>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
