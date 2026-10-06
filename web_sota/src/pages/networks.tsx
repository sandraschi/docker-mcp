import { AlertCircle, ArrowDown, ArrowUp, Loader2, Network } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ExportButtons } from "@/components/export-buttons";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useViewMode, ViewToggle } from "@/components/view-toggle";
import { API_BASE } from "@/lib/api";
import type { Column } from "@/lib/export";
import { formatAge, formatDate, resourceHref, shortId, truncate } from "@/lib/format";
import { PAGE_SIZES, type SortDir, useClientTable } from "@/lib/useClientTable";

interface NetworkItem {
  id: string;
  name: string;
  driver?: string;
  scope?: string;
  created?: string;
  internal?: boolean;
  enable_ipv6?: boolean;
  container_count?: number;
  subnet?: string | null;
  subnets?: string[];
  gateway?: string | null;
  labels?: Record<string, string>;
}

const matchNetwork = (n: NetworkItem, q: string) => {
  const hay = [n.name, n.id, n.driver, n.scope, n.subnet, n.internal ? "internal" : "external"]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return hay.includes(q);
};

const sortValue = (n: NetworkItem, key: string): string | number => {
  switch (key) {
    case "driver":
      return n.driver || "";
    case "scope":
      return n.scope || "";
    case "containers":
      return n.container_count ?? 0;
    case "created":
      return n.created || "";
    case "subnet":
      return n.subnet || "";
    default:
      return n.name || "";
  }
};

const NETWORK_COLUMNS: Array<Column<NetworkItem>> = [
  { key: "name", label: "Name", value: (n) => n.name },
  { key: "id", label: "ID", value: (n) => n.id },
  { key: "driver", label: "Driver", value: (n) => n.driver },
  { key: "scope", label: "Scope", value: (n) => n.scope },
  { key: "subnet", label: "Subnet", value: (n) => n.subnet },
  { key: "gateway", label: "Gateway", value: (n) => n.gateway },
  { key: "containers", label: "ContainerCount", value: (n) => n.container_count },
  { key: "internal", label: "Internal", value: (n) => (n.internal ? "yes" : "no") },
  { key: "ipv6", label: "IPv6", value: (n) => (n.enable_ipv6 ? "yes" : "no") },
  { key: "created", label: "Created", value: (n) => n.created },
];

export function Networks() {
  const [networks, setNetworks] = useState<NetworkItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [driverFilter, setDriverFilter] = useState("all");
  const [sortKey, setSortKey] = useState("name");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(50);
  const [viewMode, setViewMode] = useViewMode("docker-mcp:networks:view", "list");

  const fetchNetworks = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/networks`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setNetworks(data.networks ?? []);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load networks");
      setNetworks([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNetworks();
  }, []);

  const drivers = useMemo(() => {
    const set = new Set(networks.map((n) => n.driver).filter(Boolean) as string[]);
    return [...set].sort();
  }, [networks]);

  const filtered = useMemo(() => {
    if (driverFilter === "all") return networks;
    return networks.filter((n) => n.driver === driverFilter);
  }, [networks, driverFilter]);

  const match = useCallback(matchNetwork, []);
  const getSort = useCallback(sortValue, []);
  const table = useClientTable(filtered, {
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
  }, [search, pageSize, driverFilter, viewMode]);

  const toggleSort = (key: string) => {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortKey(key);
      setSortDir(key === "created" || key === "containers" ? "desc" : "asc");
    }
  };

  const totalAttached = networks.reduce((sum, n) => sum + (n.container_count ?? 0), 0);

  if (loading && networks.length === 0) {
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
          <h2 className="text-2xl font-bold tracking-tight text-white">Networks</h2>
          <p className="text-slate-400">
            {table.filteredCount} of {networks.length} networks · {totalAttached} attached endpoints
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <ViewToggle mode={viewMode} onChange={setViewMode} />
          <ExportButtons base="networks" columns={NETWORK_COLUMNS} rows={table.sortedFull} />
          <button
            type="button"
            onClick={fetchNetworks}
            disabled={loading}
            className="rounded-md bg-slate-800 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700 disabled:opacity-50"
          >
            {loading ? "Refreshing…" : "Refresh"}
          </button>
          <Link
            to="/tools/create_network"
            className="rounded-md bg-slate-800 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700"
          >
            Create
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
          <CardTitle className="text-white">Docker networks</CardTitle>
          <div className="flex flex-wrap gap-3">
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter name, driver, subnet, id…"
              className="max-w-sm bg-slate-900 border-slate-700 text-slate-100"
            />
            <select
              value={driverFilter}
              onChange={(e) => setDriverFilter(e.target.value)}
              className="h-10 rounded-md border border-slate-700 bg-slate-900 px-3 text-sm text-slate-200"
            >
              <option value="all">All drivers</option>
              {drivers.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
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
            <p className="text-slate-500 py-8 text-center">No networks match.</p>
          ) : viewMode === "list" ? (
            <>
              <div className="overflow-x-auto rounded-md border border-slate-800/60">
                <table className="w-full min-w-[900px] text-sm">
                  <thead className="bg-slate-900/80">
                    <tr className="text-left text-xs uppercase tracking-wide text-slate-400">
                      <SortTh
                        label="Name"
                        k="name"
                        sortKey={sortKey}
                        sortDir={sortDir}
                        onClick={toggleSort}
                      />
                      <th className="px-3 py-2 font-medium">ID</th>
                      <SortTh
                        label="Driver"
                        k="driver"
                        sortKey={sortKey}
                        sortDir={sortDir}
                        onClick={toggleSort}
                      />
                      <SortTh
                        label="Scope"
                        k="scope"
                        sortKey={sortKey}
                        sortDir={sortDir}
                        onClick={toggleSort}
                      />
                      <SortTh
                        label="Subnet"
                        k="subnet"
                        sortKey={sortKey}
                        sortDir={sortDir}
                        onClick={toggleSort}
                      />
                      <SortTh
                        label="Containers"
                        k="containers"
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
                    {table.rows.map((n) => (
                      <tr key={n.id} className="text-slate-200 hover:bg-slate-800/40">
                        <td className="max-w-[240px] px-3 py-2.5 align-top">
                          <Link
                            to={resourceHref("networks", n.id)}
                            className="flex items-center gap-2 text-blue-400 hover:underline"
                          >
                            <Network className="h-4 w-4 shrink-0 text-blue-500" />
                            <span className="truncate font-medium" title={n.name}>
                              {truncate(n.name, 32)}
                            </span>
                          </Link>
                          <span className="mt-1 flex flex-wrap gap-1 pl-6">
                            {n.internal ? (
                              <span className="inline-flex items-center rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 text-[11px] text-slate-400">
                                internal
                              </span>
                            ) : null}
                            {n.enable_ipv6 ? (
                              <span className="inline-flex items-center rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 text-[11px] text-slate-400">
                                IPv6
                              </span>
                            ) : null}
                          </span>
                        </td>
                        <td className="px-3 py-2.5 align-top font-mono text-xs text-slate-400">
                          {shortId(n.id)}
                        </td>
                        <td className="px-3 py-2.5 align-top">
                          <span className="inline-flex items-center rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 text-xs text-slate-200">
                            {n.driver || "—"}
                          </span>
                        </td>
                        <td className="px-3 py-2.5 align-top text-slate-300">{n.scope || "—"}</td>
                        <td className="px-3 py-2.5 align-top font-mono text-xs text-slate-300">
                          {n.subnet ? (
                            <span title={n.subnet}>{truncate(n.subnet, 24)}</span>
                          ) : (
                            <span className="text-slate-600">—</span>
                          )}
                        </td>
                        <td className="px-3 py-2.5 align-top">
                          <span
                            className={`inline-flex min-w-[2rem] items-center justify-center rounded-full px-2 py-0.5 text-xs font-semibold ${
                              (n.container_count ?? 0) > 0
                                ? "bg-blue-950/80 text-blue-300 border border-blue-800"
                                : "bg-slate-800 text-slate-400 border border-slate-700"
                            }`}
                          >
                            {n.container_count ?? 0}
                          </span>
                        </td>
                        <td className="px-3 py-2.5 align-top whitespace-nowrap">
                          <span className="block text-[13px] font-medium text-slate-200">
                            {formatAge(n.created)}
                          </span>
                          <span className="block text-[11px] text-slate-500">
                            {formatDate(n.created)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Pager page={table.page} pageCount={table.pageCount} onPage={setPage} />
            </>
          ) : (
            <>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                {table.rows.map((n) => (
                  <div
                    key={n.id}
                    className="flex flex-col rounded-lg border border-slate-800 bg-slate-900/60 p-4 transition-colors hover:border-slate-700 hover:bg-slate-900"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <Link
                        to={resourceHref("networks", n.id)}
                        className="flex min-w-0 items-center gap-2 text-blue-400 hover:underline"
                      >
                        <Network className="h-4 w-4 shrink-0 text-blue-500" />
                        <span className="truncate font-semibold text-slate-100" title={n.name}>
                          {truncate(n.name, 36)}
                        </span>
                      </Link>
                      <span className="inline-flex shrink-0 items-center rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 text-[11px] text-slate-300">
                        {n.driver || "—"}
                      </span>
                    </div>
                    <p className="mt-1 font-mono text-[11px] text-slate-500">{shortId(n.id)}</p>
                    <div className="mt-3 grid grid-cols-2 gap-3 text-[13px]">
                      <div>
                        <p className="text-[11px] uppercase tracking-wide text-slate-500">Subnet</p>
                        <p
                          className="truncate font-mono text-xs text-slate-200"
                          title={n.subnet ?? ""}
                        >
                          {n.subnet || "—"}
                        </p>
                      </div>
                      <div>
                        <p className="text-[11px] uppercase tracking-wide text-slate-500">Scope</p>
                        <p className="text-slate-200">{n.scope || "—"}</p>
                      </div>
                      <div>
                        <p className="text-[11px] uppercase tracking-wide text-slate-500">
                          Containers
                        </p>
                        <p className="font-semibold text-slate-100">{n.container_count ?? 0}</p>
                      </div>
                      <div>
                        <p className="text-[11px] uppercase tracking-wide text-slate-500">Age</p>
                        <p className="font-medium text-slate-200" title={formatDate(n.created)}>
                          {formatAge(n.created)}
                        </p>
                      </div>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {n.internal && (
                        <span className="rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 text-[11px] text-slate-400">
                          internal
                        </span>
                      )}
                      {n.enable_ipv6 && (
                        <span className="rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 text-[11px] text-slate-400">
                          IPv6 enabled
                        </span>
                      )}
                      {!n.internal && !n.enable_ipv6 && (
                        <span className="text-[11px] text-slate-600">external · IPv4</span>
                      )}
                    </div>
                    <div className="mt-3 border-t border-slate-800 pt-3">
                      <Link
                        to={resourceHref("networks", n.id)}
                        className="text-[13px] font-medium text-blue-400 hover:underline"
                      >
                        View details →
                      </Link>
                    </div>
                  </div>
                ))}
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
