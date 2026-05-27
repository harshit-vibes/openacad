type Kpi = { label: string; value: string | number };

export function PageHeader({
  title,
  description,
  kpis,
}: {
  title: string;
  description?: string;
  kpis?: Kpi[];
}) {
  return (
    <header className="mb-8 flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description && (
          <p className="text-sm text-muted-foreground mt-1.5 max-w-2xl">
            {description}
          </p>
        )}
      </div>
      {kpis && kpis.length > 0 && (
        <dl className="flex flex-wrap gap-6 md:gap-8">
          {kpis.map((k) => (
            <div key={k.label}>
              <dt className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
                {k.label}
              </dt>
              <dd className="text-xl font-semibold tabular-nums">{k.value}</dd>
            </div>
          ))}
        </dl>
      )}
    </header>
  );
}
