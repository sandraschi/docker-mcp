import { AlertCircle, ArrowDown, ArrowUp, Box, Loader2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { API_BASE } from "@/lib/api";
import { formatDate, resourceHref, shortId } from "@/lib/format";
import { PAGE_SIZES, type SortDir, useClientTable } from "@/lib/useClientTable";

interface ContainerItem {
  id: string;
  name: string;
  status: string;
  image: string;
  state: string;
  created?: string;
  ports?: string[];
  compose_project?: string | null;
  compose_service?: string | null;
  networks?: string[];
  command?: string | null;
}

const matchContainer = (c: ContainerItem, q: string) => {
  const hay = [
    c.name,
    c.id,
    c.image,
    c.state,
    c.status,
    c.compose_project,
    c.compose_service,
    ...(c.ports || []),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return hay.includes(q);
};

const sortValue = (c: ContainerItem, key: string): string | number => {
  switch (key) {
    case "name":
      return c.name || "";
    case "image":
      return c.image || "";
    case "state":
      return c.state || "";
    case "created":
      return c.created || "";
    case "ports":
      return (c.ports || []).join(", ");
    case "project":
      return c.compose_project || "";
    default:
      return c.name || "";
  }
};

export function Containers() {
  const [containers, setContainers] = useState<ContainerItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [stateFilter, setStateFilter] = useState("all");
  const [sortKey, setSortKey] = useState("name");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(50);

  const fetchContainers = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/containers`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setContainers(data.containers ?? []);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load containers");
      setContainers([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchContainers();
  }, []);

  const filteredByState = useMemo(() => {
    if (stateFilter === "all") return containers;
    if (stateFilter === "running") return containers.filter((c) => c.state === "running");
    return containers.filter((c) => c.state !== "running");
  }, [containers, stateFilter]);

  const match = useCallback(matchContainer, []);
  const getSort = useCallback(sortValue, []);

  const table = useClientTable(filteredByState, {
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
  }, [search, stateFilter, pageSize]);

  const toggleSort = (key: string) => {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortKey(key);
      setSortDir(key === "created" ? "desc" : "asc");
    }
  };

  if (loading && containers.length === 0) {
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
          <h2 className="text-2xl font-bold tracking-tight text-white">Containers</h2>
          <p className="text-slate-400">
            {table.filteredCount} of {containers.length} containers
          </p>
        </div>
        <button
          type="button"
          onClick={fetchContainers}
          disabled={loading}
          className="rounded-md bg-slate-800 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700 disabled:opacity-50"
        >
          {loading ? "Refreshing…" : "Refresh"}
        </button>
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
          <CardTitle className="text-white">All containers</CardTitle>
          <div className="flex flex-wrap gap-3">
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter name, image, id, ports, compose…"
              className="max-w-sm bg-slate-900 border-slate-700 text-slate-100"
            />
            <select
              value={stateFilter}
              onChange={(e) => setStateFilter(e.target.value)}
              className="h-10 rounded-md border border-slate-700 bg-slate-900 px-3 text-sm text-slate-200"
            >
              <option value="all">All states</option>
              <option value="running">Running</option>
              <option value="stopped">Not running</option>
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
            <p className="text-slate-500 py-8 text-center">No containers match.</p>
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
                        label="Image"
                        k="image"
                        sortKey={sortKey}
                        sortDir={sortDir}
                        onClick={toggleSort}
                      />
                      <SortTh
                        label="State"
                        k="state"
                        sortKey={sortKey}
                        sortDir={sortDir}
                        onClick={toggleSort}
                      />
                      <SortTh
                        label="Ports"
                        k="ports"
                        sortKey={sortKey}
                        sortDir={sortDir}
                        onClick={toggleSort}
                      />
                      <SortTh
                        label="Project"
                        k="project"
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
                    {table.rows.map((c) => (
                      <tr
                        key={c.id}
                        className="border-b border-slate-800/80 text-slate-200 hover:bg-slate-800/40"
                      >
                        <td className="py-3 pr-4">
                          <Link
                            to={resourceHref("containers", c.id)}
                            className="flex items-center gap-2 text-blue-400 hover:underline"
                          >
                            <Box className="h-4 w-4 text-blue-500 shrink-0" />
                            {c.name}
                          </Link>
                        </td>
                        <td className="py-3 pr-4 font-mono text-slate-400">{shortId(c.id)}</td>
                        <td className="py-3 pr-4">
                          {c.image ? (
                            <Link
                              to={resourceHref("images", c.image)}
                              className="text-slate-200 hover:text-blue-400 hover:underline"
                            >
                              {c.image}
                            </Link>
                          ) : (
                            "—"
                          )}
                        </td>
                        <td className="py-3 pr-4">
                          <span
                            className={
                              c.state === "running" ? "text-emerald-400" : "text-slate-500"
                            }
                          >
                            {c.state}
                          </span>
                          {c.status && c.status !== c.state && (
                            <span className="block text-xs text-slate-500">{c.status}</span>
                          )}
                        </td>
                        <td className="py-3 pr-4 font-mono text-xs text-slate-300">
                          {c.ports?.length ? c.ports.join(", ") : "—"}
                        </td>
                        <td className="py-3 pr-4 text-xs">
                          {c.compose_project ? (
                            <span>
                              {c.compose_project}
                              {c.compose_service ? (
                                <span className="text-slate-500"> / {c.compose_service}</span>
                              ) : null}
                            </span>
                          ) : (
                            "—"
                          )}
                        </td>
                        <td className="py-3 text-slate-400 whitespace-nowrap">
                          {formatDate(c.created)}
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
