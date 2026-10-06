import { AlertCircle, ArrowDown, ArrowUp, Box, Loader2, Terminal } from "lucide-react";
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
  labels?: Record<string, string>;
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
    c.command,
    ...(c.ports || []),
    ...(c.networks || []),
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
      return (c.ports || []).length;
    case "networks":
      return (c.networks || []).length;
    case "project":
      return c.compose_project || "";
    default:
      return c.name || "";
  }
};

function StateBadge({ state }: { state: string }) {
  const running = state === "running";
  const paused = state === "paused";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium whitespace-nowrap ${
        running
          ? "border-emerald-800 bg-emerald-950/60 text-emerald-300"
          : paused
            ? "border-amber-800 bg-amber-950/60 text-amber-300"
            : "border-slate-700 bg-slate-800/60 text-slate-300"
      }`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${running ? "bg-emerald-400" : paused ? "bg-amber-400" : "bg-slate-500"}`}
      />
      {state || "—"}
    </span>
  );
}

function ContainerActions({
  id,
  state,
  acting,
  onAction,
}: {
  id: string;
  state: string;
  acting: Record<string, string>;
  onAction: (id: string, action: "start" | "stop" | "restart") => void;
}) {
  const busy = acting[id];
  const running = state === "running";
  const btn = "rounded-md px-2 py-1 text-[11px] font-medium disabled:opacity-50 whitespace-nowrap";
  return (
    <span className="inline-flex flex-wrap gap-1">
      {!running && (
        <button
          type="button"
          disabled={Boolean(busy)}
          onClick={() => onAction(id, "start")}
          className={`${btn} bg-emerald-800 text-emerald-100 hover:bg-emerald-700`}
        >
          {busy === "start" ? "Starting…" : "Start"}
        </button>
      )}
      {running && (
        <>
          <button
            type="button"
            disabled={Boolean(busy)}
            onClick={() => onAction(id, "stop")}
            className={`${btn} bg-red-800 text-red-100 hover:bg-red-700`}
          >
            {busy === "stop" ? "Stopping…" : "Stop"}
          </button>
          <button
            type="button"
            disabled={Boolean(busy)}
            onClick={() => onAction(id, "restart")}
            className={`${btn} bg-amber-800 text-amber-100 hover:bg-amber-700`}
          >
            {busy === "restart" ? "Restarting…" : "Restart"}
          </button>
        </>
      )}
    </span>
  );
}

function Chip({ children, title }: { children: React.ReactNode; title?: string }) {
  return (
    <span
      title={title ?? (typeof children === "string" ? children : undefined)}
      className="inline-flex max-w-[220px] items-center truncate rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[11px] text-slate-300"
    >
      <span className="truncate">{children}</span>
    </span>
  );
}

const CONTAINER_COLUMNS: Array<Column<ContainerItem>> = [
  { key: "name", label: "Name", value: (c) => c.name },
  { key: "id", label: "ID", value: (c) => c.id },
  { key: "image", label: "Image", value: (c) => c.image },
  { key: "state", label: "State", value: (c) => c.state },
  { key: "status", label: "Status", value: (c) => c.status },
  { key: "ports", label: "Ports", value: (c) => (c.ports || []).join("; ") },
  { key: "networks", label: "Networks", value: (c) => (c.networks || []).join("; ") },
  { key: "project", label: "ComposeProject", value: (c) => c.compose_project },
  { key: "service", label: "ComposeService", value: (c) => c.compose_service },
  { key: "created", label: "Created", value: (c) => c.created },
  { key: "command", label: "Command", value: (c) => c.command },
];

export function Containers() {
  const [containers, setContainers] = useState<ContainerItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [acting, setActing] = useState<Record<string, string>>({});
  const [search, setSearch] = useState("");
  const [stateFilter, setStateFilter] = useState("all");
  const [sortKey, setSortKey] = useState("name");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(50);
  const [viewMode, setViewMode] = useViewMode("docker-mcp:containers:view", "list");

  const fetchContainers = async (quiet?: boolean) => {
    if (!quiet) setLoading(true);
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

  const runAction = async (id: string, action: "start" | "stop" | "restart") => {
    setActing((m) => ({ ...m, [id]: action }));
    setActionError(null);
    try {
      const res = await fetch(`${API_BASE}/api/containers/${encodeURIComponent(id)}/${action}`, {
        method: "POST",
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      await fetchContainers(true);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : `${action} failed`);
    } finally {
      setActing((m) => {
        const next = { ...m };
        delete next[id];
        return next;
      });
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

  const runningCount = useMemo(
    () => containers.filter((c) => c.state === "running").length,
    [containers],
  );

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
  }, [search, stateFilter, pageSize, viewMode]);

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
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Containers</h2>
          <p className="text-slate-400">
            {table.filteredCount} of {containers.length} containers
            <span className="ml-2 inline-flex items-center gap-1 rounded-full border border-emerald-800 bg-emerald-950/60 px-2 py-0.5 text-xs text-emerald-300">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              {runningCount} running
            </span>
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <ViewToggle mode={viewMode} onChange={setViewMode} />
          <ExportButtons base="containers" columns={CONTAINER_COLUMNS} rows={table.sortedFull} />
          <button
            type="button"
            onClick={() => void fetchContainers()}
            disabled={loading}
            className="rounded-md bg-slate-800 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700 disabled:opacity-50"
          >
            {loading ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </div>

      {actionError && <p className="text-sm text-red-400">{actionError}</p>}

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
              placeholder="Filter name, image, id, ports, network, command, compose…"
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
          ) : viewMode === "list" ? (
            <>
              <div className="overflow-x-auto rounded-md border border-slate-800/60">
                <table className="w-full min-w-[960px] text-sm">
                  <thead className="bg-slate-900/80">
                    <tr className="text-left text-xs uppercase tracking-wide text-slate-400">
                      <SortTh
                        label="Status"
                        k="state"
                        sortKey={sortKey}
                        sortDir={sortDir}
                        onClick={toggleSort}
                      />
                      <SortTh
                        label="Name"
                        k="name"
                        sortKey={sortKey}
                        sortDir={sortDir}
                        onClick={toggleSort}
                      />
                      <SortTh
                        label="Image"
                        k="image"
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
                        label="Networks"
                        k="networks"
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
                        label="Age"
                        k="created"
                        sortKey={sortKey}
                        sortDir={sortDir}
                        onClick={toggleSort}
                      />
                      <th className="px-3 py-2 font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/80">
                    {table.rows.map((c) => (
                      <tr key={c.id} className="text-slate-200 hover:bg-slate-800/40">
                        <td className="px-3 py-2.5 align-top">
                          <StateBadge state={c.state} />
                          {c.status && c.status !== c.state && (
                            <span
                              className="mt-1 block max-w-[180px] truncate text-xs text-slate-500"
                              title={c.status}
                            >
                              {truncate(c.status, 40)}
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-2.5 align-top">
                          <Link
                            to={resourceHref("containers", c.id)}
                            className="flex max-w-[220px] items-center gap-2 text-blue-400 hover:underline"
                          >
                            <Box className="h-4 w-4 shrink-0 text-blue-500" />
                            <span className="truncate font-medium">{c.name}</span>
                          </Link>
                          <span className="mt-0.5 block font-mono text-[11px] text-slate-500">
                            {shortId(c.id)}
                          </span>
                          {c.command && (
                            <span className="mt-0.5 flex max-w-[220px] items-center gap-1 text-[11px] text-slate-500">
                              <Terminal className="h-3 w-3 shrink-0" />
                              <span className="truncate font-mono" title={c.command}>
                                {truncate(c.command, 48)}
                              </span>
                            </span>
                          )}
                        </td>
                        <td className="max-w-[240px] px-3 py-2.5 align-top">
                          {c.image ? (
                            <Link
                              to={resourceHref("images", c.image)}
                              className="block truncate font-mono text-xs text-slate-200 hover:text-blue-400 hover:underline"
                              title={c.image}
                            >
                              {c.image}
                            </Link>
                          ) : (
                            <span className="text-slate-500">—</span>
                          )}
                        </td>
                        <td className="max-w-[260px] px-3 py-2.5 align-top">
                          {c.ports?.length ? (
                            <span className="flex flex-wrap gap-1">
                              {c.ports.slice(0, 3).map((p) => (
                                <Chip key={p}>{p}</Chip>
                              ))}
                              {c.ports.length > 3 && (
                                <span className="text-[11px] text-slate-500">
                                  +{c.ports.length - 3} more
                                </span>
                              )}
                            </span>
                          ) : (
                            <span className="text-slate-600">—</span>
                          )}
                        </td>
                        <td className="max-w-[200px] px-3 py-2.5 align-top">
                          {c.networks?.length ? (
                            <span className="flex flex-wrap gap-1">
                              {c.networks.slice(0, 3).map((n) => (
                                <span
                                  key={n}
                                  className="inline-flex items-center truncate rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 text-[11px] text-slate-300"
                                  title={n}
                                >
                                  {truncate(n, 22)}
                                </span>
                              ))}
                              {c.networks.length > 3 && (
                                <span className="text-[11px] text-slate-500">
                                  +{c.networks.length - 3}
                                </span>
                              )}
                            </span>
                          ) : (
                            <span className="text-slate-600">—</span>
                          )}
                        </td>
                        <td className="px-3 py-2.5 align-top text-xs">
                          {c.compose_project ? (
                            <span className="block max-w-[160px]">
                              <span
                                className="block truncate font-medium text-slate-200"
                                title={c.compose_project}
                              >
                                {c.compose_project}
                              </span>
                              {c.compose_service && (
                                <span
                                  className="block truncate text-slate-500"
                                  title={c.compose_service}
                                >
                                  {c.compose_service}
                                </span>
                              )}
                            </span>
                          ) : (
                            <span className="text-slate-600">—</span>
                          )}
                        </td>
                        <td className="px-3 py-2.5 align-top whitespace-nowrap">
                          <span className="block text-[13px] font-medium text-slate-200">
                            {formatAge(c.created)}
                          </span>
                          <span className="block text-[11px] text-slate-500">
                            {formatDate(c.created)}
                          </span>
                        </td>
                        <td className="px-3 py-2.5 align-top whitespace-nowrap">
                          <ContainerActions
                            id={c.id}
                            state={c.state}
                            acting={acting}
                            onAction={runAction}
                          />
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
                {table.rows.map((c) => (
                  <div
                    key={c.id}
                    className="flex flex-col rounded-lg border border-slate-800 bg-slate-900/60 p-4 transition-colors hover:border-slate-700 hover:bg-slate-900"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <Link
                        to={resourceHref("containers", c.id)}
                        className="flex min-w-0 items-center gap-2 text-blue-400 hover:underline"
                      >
                        <Box className="h-4 w-4 shrink-0 text-blue-500" />
                        <span className="truncate font-semibold text-slate-100">{c.name}</span>
                      </Link>
                      <StateBadge state={c.state} />
                    </div>
                    <p className="mt-1 truncate font-mono text-[11px] text-slate-500" title={c.id}>
                      {shortId(c.id)}
                    </p>
                    <div className="mt-3 space-y-2 text-[13px]">
                      <div className="min-w-0">
                        <p className="text-[11px] uppercase tracking-wide text-slate-500">Image</p>
                        <p className="truncate font-mono text-xs text-slate-200" title={c.image}>
                          {c.image || "—"}
                        </p>
                      </div>
                      <div className="flex items-center justify-between gap-2">
                        <div>
                          <p className="text-[11px] uppercase tracking-wide text-slate-500">Age</p>
                          <p className="font-medium text-slate-200" title={formatDate(c.created)}>
                            {formatAge(c.created)}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-[11px] uppercase tracking-wide text-slate-500">
                            Project
                          </p>
                          <p
                            className="max-w-[160px] truncate text-slate-200"
                            title={c.compose_project ?? ""}
                          >
                            {c.compose_project ?? "—"}
                            {c.compose_service ? (
                              <span className="text-slate-500"> / {c.compose_service}</span>
                            ) : null}
                          </p>
                        </div>
                      </div>
                      {c.ports?.length ? (
                        <div>
                          <p className="text-[11px] uppercase tracking-wide text-slate-500">
                            Ports ({c.ports.length})
                          </p>
                          <div className="mt-1 flex flex-wrap gap-1">
                            {c.ports.slice(0, 4).map((p) => (
                              <Chip key={p}>{p}</Chip>
                            ))}
                            {c.ports.length > 4 && (
                              <span className="text-[11px] text-slate-500">
                                +{c.ports.length - 4}
                              </span>
                            )}
                          </div>
                        </div>
                      ) : null}
                      {c.networks?.length ? (
                        <div>
                          <p className="text-[11px] uppercase tracking-wide text-slate-500">
                            Networks
                          </p>
                          <div className="mt-1 flex flex-wrap gap-1">
                            {c.networks.map((n) => (
                              <span
                                key={n}
                                className="inline-flex items-center rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 text-[11px] text-slate-300"
                                title={n}
                              >
                                {truncate(n, 24)}
                              </span>
                            ))}
                          </div>
                        </div>
                      ) : null}
                      {c.command && (
                        <div className="min-w-0">
                          <p className="text-[11px] uppercase tracking-wide text-slate-500">
                            Command
                          </p>
                          <p
                            className="truncate font-mono text-[11px] text-slate-400"
                            title={c.command}
                          >
                            {truncate(c.command, 72)}
                          </p>
                        </div>
                      )}
                    </div>
                    <div className="mt-3 flex items-center justify-between gap-2 border-t border-slate-800 pt-3">
                      <Link
                        to={resourceHref("containers", c.id)}
                        className="text-[13px] font-medium text-blue-400 hover:underline"
                      >
                        View details →
                      </Link>
                      <ContainerActions
                        id={c.id}
                        state={c.state}
                        acting={acting}
                        onAction={runAction}
                      />
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
