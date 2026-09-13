import { AlertCircle, ArrowDown, ArrowUp, Loader2, Network } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { API_BASE } from "@/lib/api";
import { formatDate, resourceHref, shortId } from "@/lib/format";
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
}

const matchNetwork = (n: NetworkItem, q: string) => {
  const hay = [n.name, n.id, n.driver, n.scope, n.subnet].filter(Boolean).join(" ").toLowerCase();
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
    default:
      return n.name || "";
  }
};

export function Networks() {
  const [networks, setNetworks] = useState<NetworkItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState("name");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(50);

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

  const match = useCallback(matchNetwork, []);
  const getSort = useCallback(sortValue, []);
  const table = useClientTable(networks, {
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
  }, [search, pageSize]);

  const toggleSort = (key: string) => {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortKey(key);
      setSortDir(key === "created" || key === "containers" ? "desc" : "asc");
    }
  };

  if (loading && networks.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[320px]">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Networks</h2>
          <p className="text-slate-400">
            {table.filteredCount} of {networks.length} networks
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
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
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-800 text-left text-slate-400">
                      <SortTh
                        label="Name"
                        k="name"
                        sortKey={sortKey}
                        sortDir={sortDir}
                        onClick={toggleSort}
                      />
                      <th className="pb-2 pr-4 font-medium">ID</th>
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
                      <th className="pb-2 pr-4 font-medium">Subnet</th>
                      <SortTh
                        label="Containers"
                        k="containers"
                        sortKey={sortKey}
                        sortDir={sortDir}
                        onClick={toggleSort}
                      />
                      <SortTh
                        label="Created"
                        k="created"
                        sortKey={sortKey}
                        sortDir={sortDir}
                        onClick={toggleSort}
                      />
                    </tr>
                  </thead>
                  <tbody>
                    {table.rows.map((n) => (
                      <tr
                        key={n.id}
                        className="border-b border-slate-800/80 text-slate-200 hover:bg-slate-800/40"
                      >
                        <td className="py-3 pr-4">
                          <Link
                            to={resourceHref("networks", n.id)}
                            className="flex items-center gap-2 text-blue-400 hover:underline"
                          >
                            <Network className="h-4 w-4 text-blue-500 shrink-0" />
                            {n.name}
                          </Link>
                          {n.internal ? (
                            <span className="ml-2 text-xs text-slate-500">internal</span>
                          ) : null}
                        </td>
                        <td className="py-3 pr-4 font-mono text-slate-400">{shortId(n.id)}</td>
                        <td className="py-3 pr-4">{n.driver || "—"}</td>
                        <td className="py-3 pr-4">{n.scope || "—"}</td>
                        <td className="py-3 pr-4 font-mono text-xs">{n.subnet || "—"}</td>
                        <td className="py-3 pr-4">{n.container_count ?? 0}</td>
                        <td className="py-3 text-slate-400 whitespace-nowrap">
                          {formatDate(n.created)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
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
    <th className="pb-2 pr-4 font-medium">
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
