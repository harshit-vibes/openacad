import { api } from "@/lib/api";

import { AtomsTable } from "./atoms-table";
import { PageHeader } from "@/components/page-header";

export default async function VaultPage() {
  const [list, stats] = await Promise.all([
    api.atoms({ limit: 50 }).catch((e) => ({
      atoms: [],
      total: 0,
      limit: 50,
      offset: 0,
      __error: String(e),
    })),
    api.stats().catch(() => null),
  ]);

  const types = stats ? Object.keys(stats.by_type ?? {}) : [];
  const domains = stats ? Object.keys(stats.by_domain ?? {}) : [];

  return (
    <div className="px-6 md:px-10 py-8 max-w-7xl mx-auto">
      <PageHeader
        title="Vault"
        description="Every atom, every relation, every source span — all on disk."
        kpis={
          stats
            ? [
                { label: "Atoms", value: stats.n_atoms.toLocaleString() },
                { label: "Relations", value: stats.n_relations.toLocaleString() },
                { label: "Sources", value: stats.n_sources.toLocaleString() },
                {
                  label: "Attributes",
                  value: stats.n_attributes.toLocaleString(),
                },
              ]
            : undefined
        }
      />

      {"__error" in list && (list as { __error?: string }).__error && (
        <div className="my-4 text-sm text-destructive">
          API error: {(list as { __error: string }).__error}
        </div>
      )}

      <AtomsTable initial={list as never} types={types} domains={domains} />
    </div>
  );
}
