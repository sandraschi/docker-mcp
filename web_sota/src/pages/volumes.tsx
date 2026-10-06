import { AlertCircle, ArrowDown, ArrowUp, Database, Loader2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ExportButtons } from "@/components/export-buttons";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useViewMode, ViewToggle } from "@/components/view-toggle";
import { API_BASE } from "@/lib/api";
import type { Column } from "@/lib/export";
import { formatAge, formatBytes, formatDate, resourceHref, truncate } from "@/lib/format";
import { PAGE_SIZES, type SortDir, useClientTable } from "@/lib/useClientTable";

interface VolumeItem {
  name: string;
  driver?: string;
  mountpoint?: string;
  created?: string;
  scope?: string;
  ref_count?: number | null;
  size?: number | null;
  labels?: Record<string, string>;
  options?: Record<string, string>;
}

const matchVolume = (v: VolumeItem, q: string) => {
  const hay = [
    v.name,
    v.driver,
    v.mountpoint,
    v.scope,
    (v.ref_count ?? 0) > 0 ? "in-use" : "unused",
  ]
    .filter((x): x is string => typeof x === "string" && x.length > 0)
    .join(" ")
    .toLowerCase();
  return hay.includes(q);
};

const sortValue = (v: VolumeItem, key: string): string | number => {
  switch (key) {
    case "driver":
      return v.driver || "";
    case "created":
      return v.created || "";
    case "refs":
      return v.ref_count ?? -1;
    case "size":
      return v.size ?? -1;
    default:
      return v.name || "";
  }
};

function RefsBadge({ count }: { count: number | null | undefined }) {
  if (count == null) return <span className="text-slate-600">—</span>;
  const inUse = count > 0;
  return (
    <span
      className={`inline-flex min-w-[2rem] items-center justify-center rounded-full border px-2 py-0.5 text-xs font-semibold ${
        inUse
          ? "border-blue-800 bg-blue-950/80 text-blue-300"
          : "border-slate-700 bg-slate-800 text-slate-400"
      }`}
      title={inUse ? `Referenced by ${count} container${count === 1 ? "" : "s"}` : "Not referenced"}
    >
      {inUse ? `in use · ${count}` : "unused"}
    </span>
  );
}

const VOLUME_COLUMNS: Array<Column<VolumeItem>> = [
  { key: "name", label: "Name", value: (v) => v.name },
  { key: "driver", label: "Driver", value: (v) => v.driver },
  { key: "mountpoint", label: "Mountpoint", value: (v) => v.mountpoint },
  { key: "scope", label: "Scope", value: (v) => v.scope },
  { key: "refs", label: "RefCount", value: (v) => v.ref_count },
  { key: "size", label: "SizeBytes", value: (v) => v.size },
  { key: "created", label: "Created", value: (v) => v.created },
];

export function Volumes() {
  const [volumes, setVolumes] = useState<VolumeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [usageFilter, setUsageFilter] = useState("all");
  const [sortKey, setSortKey] = useState("name");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(50);
  const [viewMode, setViewMode] = useViewMode("docker-mcp:volumes:view", "list");

  const fetchVolumes = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/volumes`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setVolumes(data.volumes ?? []);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load volumes");
      setVolumes([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVolumes();
  }, []);

  const filteredByUsage = useMemo(() => {
    if (usageFilter === "in-use") return volumes.filter((v) => (v.ref_count ?? 0) > 0);
    if (usageFilter === "unused") return volumes.filter((v) => (v.ref_count ?? 0) <= 0);
    return volumes;
  }, [volumes, usageFilter]);

  const totalSize = useMemo(
    () => filteredByUsage.reduce((sum, v) => sum + (v.size || 0), 0),
    [filteredByUsage],
  );
  const inUseCount = useMemo(() => volumes.filter((v) => (v.ref_count ?? 0) > 0).length, [volumes]);

  const match = useCallback(matchVolume, []);
  const getSort = useCallback(sortValue, []);
  const table = useClientTable(filteredByUsage, {
    search,
    match,
    sortKey,
    sortDir,
    sortValue: getSort,
    page,
    pageSize,
  });

  useEffect(() => {
    setPage(0);
  }, [search, pageSize, usageFilter, viewMode]);

  const toggleSort = (key: string) => {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortKey(key);
      setSortDir(key === "created" || key === "size" ? "desc" : "asc");
    }
  };

  if (loading && volumes.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[320px]">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Volumes</h2>
          <p className="text-slate-400">
            {table.filteredCount} of {volumes.length} volumes · {inUseCount} in use
            {totalSize > 0 && <span> · {formatBytes(totalSize)} reported</span>}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <ViewToggle mode={viewMode} onChange={setViewMode} />
          <ExportButtons base="volumes" columns={VOLUME_COLUMNS} rows={table.sortedFull} />
          <button
            type="button"
            onClick={fetchVolumes}
            disabled={loading}
            className="rounded-md bg-slate-800 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700 disabled:opacity-50"
          >
            {loading ? "Refreshing…" : "Refresh"}
          </button>
          <Link
            to="/tools/create_volume"
            className="rounded-md bg-slate-800 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700"
          >
            Create
          </Link>
          <Link
            to="/tools/prune_volumes"
            className="rounded-md bg-slate-800 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700"
          >
            Prune
          </Link>
        </div>
      </div>

      {error && (
        <Card className="border-red-900/50 bg-red-950/20">
          <CardContent className="flex items-center gap-3 pt-6">
            <AlertCircle className="h-8 w-8 text-red-500 shrink-0" />
            <p className="text-red-200">{error}</p>
          </CardContent>
        </Card>
      )}

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader className="space-y-4">
          <CardTitle className="text-white">Named volumes</CardTitle>
          <div className="flex flex-wrap gap-3">
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter name, driver, mountpoint…"
              className="max-w-sm bg-slate-900 border-slate-700 text-slate-100"
            />
            <select
              value={usageFilter}
              onChange={(e) => setUsageFilter(e.target.value)}
              className="h-10 rounded-md border border-slate-700 bg-slate-900 px-3 text-sm text-slate-200"
            >
              <option value="all">All volumes</option>
              <option value="in-use">In use</option>
              <option value="unused">Unused</option>
            </select>
            <select
              value={pageSize}
              onChange={(e) => setPageSize(Number(e.target.value))}
              className="h-10 rounded-md border border-slate-700 bg-slate-900 px-3 text-sm text-slate-200"
            >
              {PAGE_SIZES.map((n) => (
                <option key={n} value={n}>
                  {n} / page
                </option>
              ))}
            </select>
          </div>
        </CardHeader>
        <CardContent>
          {table.rows.length === 0 && !error ? (
            <p className="text-slate-500 py-8 text-center">No volumes match.</p>
          ) : viewMode === "list" ? (
            <>
              <div className="overflow-x-auto rounded-md border border-slate-800/60">
                <table className="w-full min-w-[960px] text-sm">
                  <thead className="bg-slate-900/80">
                    <tr className="text-left text-xs uppercase tracking-wide text-slate-400">
                      <SortTh
                        label="Name"
                        k="name"
                        sortKey={sortKey}
                        sortDir={sortDir}
                        onClick={toggleSort}
                      />
                      <SortTh
                        label="Driver"
                        k="driver"
                        sortKey={sortKey}
                        sortDir={sortDir}
                        onClick={toggleSort}
                      />
                      <th className="px-3 py-2 font-medium">Mountpoint</th>
                      <SortTh
                        label="Size"
                        k="size"
                        sortKey={sortKey}
                        sortDir={sortDir}
                        onClick={toggleSort}
                      />
                      <SortTh
                        label="Refs"
                        k="refs"
                        sortKey={sortKey}
                        sortDir={sortDir}
                        onClick={toggleSort}
                      />
                      <SortTh
                        label="Age"
                        k="created"
                        sortKey={sortKey}
                        sortDir={sortDir}
                        onClick={toggleSort}
                      />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/80">
                    {table.rows.map((v) => {
                      const labelCount = v.labels ? Object.keys(v.labels).length : 0;
                      return (
                        <tr key={v.name} className="text-slate-200 hover:bg-slate-800/40">
                          <td className="max-w-[240px] px-3 py-2.5 align-top">
                            <Link
                              to={resourceHref("volumes", v.name)}
                              className="flex items-center gap-2 text-blue-400 hover:underline"
                            >
                              <Database className="h-4 w-4 shrink-0 text-blue-500" />
                              <span className="truncate font-medium" title={v.name}>
                                {truncate(v.name, 32)}
                              </span>
                            </Link>
                            <span className="mt-0.5 block pl-6 text-[11px] text-slate-500">
                              {v.scope || "local"}
                              {labelCount > 0 ? ` · ${labelCount} labels` : ""}
                            </span>
                          </td>
                          <td className="px-3 py-2.5 align-top">
                            <span className="inline-flex items-center rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 text-xs text-slate-200">
                              {v.driver || "—"}
                            </span>
                          </td>
                          <td className="max-w-[320px] px-3 py-2.5 align-top">
                            <span
                              className="block truncate font-mono text-xs text-slate-400"
                              title={v.mountpoint || ""}
                            >
                              {v.mountpoint ? truncate(v.mountpoint, 56) : "—"}
                            </span>
                          </td>
                          <td className="px-3 py-2.5 align-top whitespace-nowrap font-medium">
                            {v.size == null ? (
                              <span className="text-slate-600">—</span>
                            ) : (
                              formatBytes(v.size)
                            )}
                          </td>
                          <td className="px-3 py-2.5 align-top">
                            <RefsBadge count={v.ref_count} />
                          </td>
                          <td className="px-3 py-2.5 align-top whitespace-nowrap">
                            <span className="block text-[13px] font-medium text-slate-200">
                              {formatAge(v.created)}
                            </span>
                            <span className="block text-[11px] text-slate-500">
                              {formatDate(v.created)}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <Pager page={table.page} pageCount={table.pageCount} onPage={setPage} />
            </>
          ) : (
            <>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                {table.rows.map((v) => {
                  const labelCount = v.labels ? Object.keys(v.labels).length : 0;
                  const optionCount = v.options ? Object.keys(v.options).length : 0;
                  return (
                    <div
                      key={v.name}
                      className="flex flex-col rounded-lg border border-slate-800 bg-slate-900/60 p-4 transition-colors hover:border-slate-700 hover:bg-slate-900"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <Link
                          to={resourceHref("volumes", v.name)}
                          className="flex min-w-0 items-center gap-2 text-blue-400 hover:underline"
                        >
                          <Database className="h-4 w-4 shrink-0 text-blue-500" />
                          <span className="truncate font-semibold text-slate-100" title={v.name}>
                            {truncate(v.name, 36)}
                          </span>
                        </Link>
                        <RefsBadge count={v.ref_count} />
                      </div>
                      <div className="mt-3 grid grid-cols-2 gap-3 text-[13px]">
                        <div>
                          <p className="text-[11px] uppercase tracking-wide text-slate-500">Size</p>
                          <p className="text-lg font-bold text-slate-100">
                            {v.size == null ? "—" : formatBytes(v.size)}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-[11px] uppercase tracking-wide text-slate-500">Age</p>
                          <p className="font-medium text-slate-200" title={formatDate(v.created)}>
                            {formatAge(v.created)}
                          </p>
                        </div>
                        <div>
                          <p className="text-[11px] uppercase tracking-wide text-slate-500">
                            Driver
                          </p>
                          <p className="text-slate-200">{v.driver || "—"}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-[11px] uppercase tracking-wide text-slate-500">
                            Scope
                          </p>
                          <p className="text-slate-200">{v.scope || "local"}</p>
                        </div>
                      </div>
                      <div className="mt-3 min-w-0">
                        <p className="text-[11px] uppercase tracking-wide text-slate-500">
                          Mountpoint
                        </p>
                        <p
                          className="truncate font-mono text-[11px] text-slate-400"
                          title={v.mountpoint || ""}
                        >
                          {v.mountpoint ? truncate(v.mountpoint, 64) : "—"}
                        </p>
                      </div>
                      <div className="mt-2 text-[11px] text-slate-500">
                        {labelCount > 0 ? `${labelCount} labels` : "no labels"}
                        {optionCount > 0 ? ` · ${optionCount} options` : ""}
                        <span className="ml-2" title={formatDate(v.created)}>
                          {formatDate(v.created)}
                        </span>
                      </div>
                      <div className="mt-3 border-t border-slate-800 pt-3">
                        <Link
                          to={resourceHref("volumes", v.name)}
                          className="text-[13px] font-medium text-blue-400 hover:underline"
                        >
                          View details →
                        </Link>
                      </div>
                    </div>
                  );
                })}
              </div>
              <Pager page={table.page} pageCount={table.pageCount} onPage={setPage} />
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function SortTh({
  label,
  k,
  sortKey,
  sortDir,
  onClick,
}: {
  label: string;
  k: string;
  sortKey: string;
  sortDir: SortDir;
  onClick: (key: string) => void;
}) {
  const active = sortKey === k;
  return (
    <th className="px-3 py-2 font-medium">
      <button
        type="button"
        onClick={() => onClick(k)}
        className="inline-flex items-center gap-1 hover:text-white"
      >
        {label}
        {active ? (
          sortDir === "asc" ? (
            <ArrowUp className="h-3 w-3" />
          ) : (
            <ArrowDown className="h-3 w-3" />
          )
        ) : null}
      </button>
    </th>
  );
}

function Pager({
  page,
  pageCount,
  onPage,
}: {
  page: number;
  pageCount: number;
  onPage: (n: number) => void;
}) {
  if (pageCount <= 1) return null;
  return (
    <div className="flex items-center justify-between pt-4 text-sm text-slate-400">
      <span>
        Page {page + 1} of {pageCount}
      </span>
      <div className="flex gap-2">
        <button
          type="button"
          disabled={page <= 0}
          onClick={() => onPage(page - 1)}
          className="rounded-md bg-slate-800 px-3 py-1.5 disabled:opacity-40"
        >
          Previous
        </button>
        <button
          type="button"
          disabled={page >= pageCount - 1}
          onClick={() => onPage(page + 1)}
          className="rounded-md bg-slate-800 px-3 py-1.5 disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  );
}
