"use client";

import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";

import { AtomSheet } from "@/components/atom-sheet";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

import { api } from "@/lib/api";
import type { AtomListResponse, AtomSummary } from "@/lib/types";

const PAGE_SIZE = 50;

export function AtomsTable({
  initial,
  types,
  domains,
}: {
  initial: AtomListResponse;
  types: string[];
  domains: string[];
}) {
  const [type, setType] = useState<string>("");
  const [domain, setDomain] = useState<string>("");
  const [q, setQ] = useState("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<AtomListResponse>(initial);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);

  // Re-query when filters change.
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .atoms({
        type: type || undefined,
        domain: domain || undefined,
        q: q || undefined,
        limit: PAGE_SIZE,
        offset,
      })
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [type, domain, q, offset]);

  // Reset to page 1 when a filter changes (but not when offset changes).
  useEffect(() => {
    setOffset(0);
  }, [type, domain, q]);

  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  const hasFilters = useMemo(
    () => Boolean(type || domain || q),
    [type, domain, q],
  );

  return (
    <>
      <div className="flex flex-wrap gap-3 mb-4 items-center">
        <div className="relative flex-1 min-w-[240px] max-w-md">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search atom id or body…"
            className="pl-8"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <Select value={type} onChange={setType} label="Type" options={types} />
        <Select
          value={domain}
          onChange={setDomain}
          label="Domain"
          options={domains}
        />
        {hasFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setType("");
              setDomain("");
              setQ("");
            }}
          >
            Clear
          </Button>
        )}
        <div className="ml-auto text-xs text-muted-foreground">
          {data.total.toLocaleString()} atoms
        </div>
      </div>

      <div className="rounded-md border border-border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[36%]">Atom</TableHead>
              <TableHead className="w-[10%]">Type</TableHead>
              <TableHead className="w-[14%]">Domain</TableHead>
              <TableHead className="w-[8%] text-right">Rels</TableHead>
              <TableHead className="w-[8%] text-right">Sources</TableHead>
              <TableHead className="w-[24%]">Tags</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading &&
              Array.from({ length: 6 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={6}>
                    <Skeleton className="h-5 w-full" />
                  </TableCell>
                </TableRow>
              ))}
            {!loading &&
              data.atoms.map((a: AtomSummary) => (
                <TableRow
                  key={a.id}
                  onClick={() => {
                    setSelected(a.id);
                    setSheetOpen(true);
                  }}
                  className="cursor-pointer"
                >
                  <TableCell>
                    <div className="font-mono text-xs">{a.id}</div>
                    <div className="text-[11px] text-muted-foreground line-clamp-1 mt-0.5">
                      {a.body_preview}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary" className="text-[10px]">
                      {a.type}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-xs">
                    {a.domain ?? (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right text-xs tabular-nums">
                    {a.n_relations}
                  </TableCell>
                  <TableCell className="text-right text-xs tabular-nums">
                    {a.n_sources}
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {a.tags.slice(0, 3).map((t) => (
                        <Badge
                          key={t}
                          variant="outline"
                          className="text-[10px] py-0"
                        >
                          {t}
                        </Badge>
                      ))}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            {!loading && data.atoms.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={6}
                  className="text-center text-sm text-muted-foreground py-12"
                >
                  No atoms match these filters.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between mt-4 text-xs text-muted-foreground">
        <span>
          Page {currentPage} of {totalPages}
        </span>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
          >
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={offset + PAGE_SIZE >= data.total}
            onClick={() => setOffset(offset + PAGE_SIZE)}
          >
            Next
          </Button>
        </div>
      </div>

      <AtomSheet
        atomId={selected}
        open={sheetOpen}
        onOpenChange={(v) => setSheetOpen(v)}
      />
    </>
  );
}

function Select({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="h-9 rounded-md border border-input bg-transparent px-2 text-xs min-w-[120px]"
      aria-label={label}
    >
      <option value="">{label}: any</option>
      {options.map((o) => (
        <option key={o} value={o}>
          {o}
        </option>
      ))}
    </select>
  );
}
