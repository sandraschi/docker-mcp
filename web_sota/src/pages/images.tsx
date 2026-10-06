import {
  AlertCircle,
  ArrowDown,
  ArrowUp,
  Download,
  Image as ImageIcon,
  Loader2,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ExportButtons } from "@/components/export-buttons";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useViewMode, ViewToggle } from "@/components/view-toggle";
import { API_BASE } from "@/lib/api";
import type { Column } from "@/lib/export";
import {
  formatAge,
  formatBytes,
  formatDate,
  imageRef,
  resourceHref,
  shortId,
  truncate,
} from "@/lib/format";
import { describeImage, kindLabel, splitRepoTag } from "@/lib/provenance";
import { PAGE_SIZES, type SortDir, useClientTable } from "@/lib/useClientTable";

interface Provenance {
  kind: string;
  fleet_repo?: string | null;
  registry?: string | null;
  namespace?: string | null;
  hub_url?: string | null;
  github_url?: string;
}

interface ImageItem {
  id: string;
  repo_tags?: string[];
  size?: number;
  shared_size?: number;
  virtual_size?: number;
  created?: string;
  dangling?: boolean;
  architecture?: string;
  os?: string;
  labels?: Record<string, string>;
  provenance?: Provenance;
  used_by?: string[];
  used_count?: number;
}

interface PullState {
  busy: boolean;
  msg: string | null;
  ok: boolean;
}

const matchImage = (img: ImageItem, q: string) => {
  const hay = [
    img.id,
    ...(img.repo_tags || []),
    img.architecture,
    img.os,
    img.provenance?.kind,
    img.provenance?.fleet_repo,
    img.provenance?.registry,
    img.dangling ? "dangling" : "tagged",
    (img.used_count ?? 0) > 0 ? "in-use" : "unused",
    ...(img.used_by || []),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return hay.includes(q);
};

const sortValue = (img: ImageItem, key: string): string | number => {
  switch (key) {
    case "tag":
      return imageRef(img);
    case "size":
      return img.size || 0;
    case "created":
      return img.created || "";
    case "id":
      return img.id || "";
    case "used":
      return img.used_count ?? 0;
    default:
      return img.size || 0;
  }
};

function KindBadge({ kind, fleetRepo }: { kind?: string; fleetRepo?: string | null }) {
  const k = kind || "local";
  const color =
    k === "local"
      ? "border-emerald-800 bg-emerald-950/60 text-emerald-300"
      : k === "dockerhub-official"
        ? "border-blue-800 bg-blue-950/60 text-blue-300"
        : k === "ghcr"
          ? "border-violet-800 bg-violet-950/60 text-violet-300"
          : "border-slate-700 bg-slate-900 text-slate-300";
  return (
    <span
      className={`inline-flex items-center whitespace-nowrap rounded-full border px-2 py-0.5 text-[11px] font-medium ${color}`}
      title={fleetRepo ? `Built from fleet repo: ${fleetRepo}` : kindLabel(k)}
    >
      {fleetRepo ? `${fleetRepo} (local)` : kindLabel(k)}
    </span>
  );
}

function UsedBadge({ count }: { count?: number }) {
  const n = count ?? 0;
  if (n > 0) {
    return (
      <span className="inline-flex items-center whitespace-nowrap rounded-full border border-blue-800 bg-blue-950/60 px-2 py-0.5 text-[11px] font-medium text-blue-300">
        in use · {n}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center whitespace-nowrap rounded-full border border-amber-800 bg-amber-950/60 px-2 py-0.5 text-[11px] font-medium text-amber-300">
      unused
    </span>
  );
}

const IMAGE_COLUMNS: Array<Column<ImageItem>> = [
  { key: "tag", label: "Tag", value: (img) => imageRef(img) },
  { key: "alltags", label: "AllTags", value: (img) => (img.repo_tags || []).join("; ") },
  { key: "id", label: "ID", value: (img) => img.id },
  { key: "size", label: "SizeBytes", value: (img) => img.size },
  { key: "shared", label: "SharedBytes", value: (img) => img.shared_size },
  { key: "os", label: "OS", value: (img) => img.os },
  { key: "arch", label: "Arch", value: (img) => img.architecture },
  { key: "created", label: "Created", value: (img) => img.created },
  { key: "kind", label: "SourceKind", value: (img) => img.provenance?.kind },
  { key: "fleet", label: "FleetRepo", value: (img) => img.provenance?.fleet_repo },
  { key: "used", label: "UsedCount", value: (img) => img.used_count },
  { key: "usedby", label: "UsedBy", value: (img) => (img.used_by || []).join("; ") },
];

export function Images() {
  const [images, setImages] = useState<ImageItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [tagFilter, setTagFilter] = useState("all");
  const [originFilter, setOriginFilter] = useState("all");
  const [usageFilter, setUsageFilter] = useState("all");
  const [sortKey, setSortKey] = useState("size");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(50);
  const [viewMode, setViewMode] = useViewMode("docker-mcp:images:view", "list");
  const [pulls, setPulls] = useState<Record<string, PullState>>({});

  const fetchImages = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/images`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setImages(data.images ?? []);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load images");
      setImages([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchImages();
  }, []);

  const pullImage = async (ref: string) => {
    const { repository, tag } = splitRepoTag(ref);
    setPulls((p) => ({ ...p, [ref]: { busy: true, msg: null, ok: false } }));
    try {
      const res = await fetch(`${API_BASE}/api/images/pull`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repository, tag }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setPulls((p) => ({ ...p, [ref]: { busy: false, msg: data.message || "done", ok: true } }));
      await fetchImages();
    } catch (e) {
      setPulls((p) => ({
        ...p,
        [ref]: { busy: false, msg: e instanceof Error ? e.message : "Pull failed", ok: false },
      }));
    }
  };

  const filtered = useMemo(() => {
    let rows = images;
    if (tagFilter === "dangling")
      rows = rows.filter((img) => img.dangling || !img.repo_tags?.length);
    if (tagFilter === "tagged")
      rows = rows.filter((img) => img.repo_tags && img.repo_tags.length > 0);
    if (originFilter === "local")
      rows = rows.filter((img) => (img.provenance?.kind || "local") === "local");
    if (originFilter === "external")
      rows = rows.filter((img) => (img.provenance?.kind || "local") !== "local");
    if (usageFilter === "unused") rows = rows.filter((img) => (img.used_count ?? 0) === 0);
    if (usageFilter === "in-use") rows = rows.filter((img) => (img.used_count ?? 0) > 0);
    return rows;
  }, [images, tagFilter, originFilter, usageFilter]);

  const match = useCallback(matchImage, []);
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
  }, [search, tagFilter, originFilter, usageFilter, pageSize, viewMode]);

  const toggleSort = (key: string) => {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortKey(key);
      setSortDir(key === "tag" ? "asc" : "desc");
    }
  };

  const totalSize = images.reduce((sum, img) => sum + (img.size || 0), 0);
  const danglingCount = images.filter((img) => img.dangling || !img.repo_tags?.length).length;
  const unusedCount = images.filter((img) => (img.used_count ?? 0) === 0 && !img.dangling).length;

  if (loading && images.length === 0) {
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
          <h2 className="text-2xl font-bold tracking-tight text-white">Images</h2>
          <p className="text-slate-400">
            {table.filteredCount} of {images.length} images · {formatBytes(totalSize)} total
            {danglingCount > 0 && (
              <span className="ml-2 inline-flex items-center rounded-full border border-amber-800 bg-amber-950/60 px-2 py-0.5 text-xs text-amber-300">
                {danglingCount} dangling
              </span>
            )}
            {unusedCount > 0 && (
              <span className="ml-2 inline-flex items-center rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 text-xs text-slate-300">
                {unusedCount} unused
              </span>
            )}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <ViewToggle mode={viewMode} onChange={setViewMode} />
          <ExportButtons base="images" columns={IMAGE_COLUMNS} rows={table.sortedFull} />
          <button
            type="button"
            onClick={fetchImages}
            disabled={loading}
            className="rounded-md bg-slate-800 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700 disabled:opacity-50"
          >
            {loading ? "Refreshing…" : "Refresh"}
          </button>
          <Link
            to="/tools/search_images"
            className="rounded-md bg-slate-800 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700"
          >
            Search Hub
          </Link>
          <Link
            to="/tools/prune_images"
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
          <CardTitle className="text-white">All images</CardTitle>
          <div className="flex flex-wrap gap-3">
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter tag, id, arch, source, usage…"
              className="max-w-sm bg-slate-900 border-slate-700 text-slate-100"
            />
            <select
              value={tagFilter}
              onChange={(e) => setTagFilter(e.target.value)}
              className="h-10 rounded-md border border-slate-700 bg-slate-900 px-3 text-sm text-slate-200"
            >
              <option value="all">All images</option>
              <option value="tagged">Tagged</option>
              <option value="dangling">Dangling</option>
            </select>
            <select
              value={originFilter}
              onChange={(e) => setOriginFilter(e.target.value)}
              className="h-10 rounded-md border border-slate-700 bg-slate-900 px-3 text-sm text-slate-200"
            >
              <option value="all">All origins</option>
              <option value="local">Local builds</option>
              <option value="external">External</option>
            </select>
            <select
              value={usageFilter}
              onChange={(e) => setUsageFilter(e.target.value)}
              className="h-10 rounded-md border border-slate-700 bg-slate-900 px-3 text-sm text-slate-200"
            >
              <option value="all">Used + unused</option>
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
            <p className="text-slate-500 py-8 text-center">No images match.</p>
          ) : viewMode === "list" ? (
            <>
              <div className="overflow-x-auto rounded-md border border-slate-800/60">
                <table className="w-full min-w-[1180px] text-sm">
                  <thead className="bg-slate-900/80">
                    <tr className="text-left text-xs uppercase tracking-wide text-slate-400">
                      <SortTh
                        label="Repository : Tag"
                        k="tag"
                        sortKey={sortKey}
                        sortDir={sortDir}
                        onClick={toggleSort}
                      />
                      <th className="px-3 py-2 font-medium">Source</th>
                      <SortTh
                        label="Size"
                        k="size"
                        sortKey={sortKey}
                        sortDir={sortDir}
                        onClick={toggleSort}
                      />
                      <SortTh
                        label="Used"
                        k="used"
                        sortKey={sortKey}
                        sortDir={sortDir}
                        onClick={toggleSort}
                      />
                      <th className="px-3 py-2 font-medium">OS / Arch</th>
                      <SortTh
                        label="Age"
                        k="created"
                        sortKey={sortKey}
                        sortDir={sortDir}
                        onClick={toggleSort}
                      />
                      <th className="px-3 py-2 font-medium">Pull</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/80">
                    {table.rows.map((img) => {
                      const ref = imageRef(img);
                      const dangling = img.dangling || !img.repo_tags?.length;
                      const pull = pulls[ref];
                      return (
                        <tr key={img.id} className="text-slate-200 hover:bg-slate-800/40">
                          <td className="max-w-[300px] px-3 py-2.5 align-top">
                            <Link
                              to={resourceHref("images", ref)}
                              className="flex items-center gap-2 text-blue-400 hover:underline"
                            >
                              <ImageIcon className="h-4 w-4 shrink-0 text-blue-500" />
                              <span className="truncate font-mono text-xs" title={ref || "<none>"}>
                                {ref || "<none>"}
                              </span>
                            </Link>
                            <span
                              className="mt-1 block truncate pl-6 font-mono text-[11px] text-slate-500"
                              title={img.id}
                            >
                              {shortId(img.id)}
                            </span>
                            {dangling ? (
                              <span className="ml-6 mt-1 inline-flex items-center rounded-full border border-amber-800 bg-amber-950/60 px-2 py-0.5 text-[11px] text-amber-300">
                                dangling
                              </span>
                            ) : null}
                          </td>
                          <td className="px-3 py-2.5 align-top">
                            <KindBadge
                              kind={img.provenance?.kind}
                              fleetRepo={img.provenance?.fleet_repo}
                            />
                          </td>
                          <td className="px-3 py-2.5 align-top whitespace-nowrap">
                            <span className="block font-semibold text-slate-100">
                              {formatBytes(img.size)}
                            </span>
                            {img.shared_size ? (
                              <span className="block text-[11px] text-slate-500">
                                shared {formatBytes(img.shared_size)}
                              </span>
                            ) : null}
                          </td>
                          <td className="px-3 py-2.5 align-top">
                            <span
                              title={
                                (img.used_by || []).join(", ") || "No container uses this image"
                              }
                            >
                              <UsedBadge count={img.used_count} />
                            </span>
                            {(img.used_by || []).length > 0 && (
                              <span
                                className="mt-1 block max-w-[160px] truncate text-[11px] text-slate-500"
                                title={(img.used_by || []).join(", ")}
                              >
                                {(img.used_by || []).slice(0, 2).join(", ")}
                                {(img.used_by || []).length > 2
                                  ? ` +${(img.used_by || []).length - 2}`
                                  : ""}
                              </span>
                            )}
                          </td>
                          <td className="px-3 py-2.5 align-top">
                            <span className="inline-flex items-center whitespace-nowrap rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 font-mono text-[11px] text-slate-300">
                              {[img.os, img.architecture].filter(Boolean).join("/") || "—"}
                            </span>
                          </td>
                          <td className="px-3 py-2.5 align-top whitespace-nowrap">
                            <span className="block text-[13px] font-medium text-slate-200">
                              {formatAge(img.created)}
                            </span>
                            <span className="block text-[11px] text-slate-500">
                              {formatDate(img.created)}
                            </span>
                          </td>
                          <td className="px-3 py-2.5 align-top whitespace-nowrap">
                            {!dangling && ref ? (
                              <>
                                <button
                                  type="button"
                                  disabled={pull?.busy}
                                  onClick={() => void pullImage(ref)}
                                  title={`Pull ${ref} (reports already-current)`}
                                  className="inline-flex items-center gap-1 rounded-md bg-slate-800 px-2 py-1 text-xs font-medium text-slate-200 hover:bg-slate-700 disabled:opacity-50"
                                >
                                  {pull?.busy ? (
                                    <Loader2 className="h-3 w-3 animate-spin" />
                                  ) : (
                                    <Download className="h-3 w-3" />
                                  )}
                                  Pull
                                </button>
                                {pull?.msg && (
                                  <span
                                    className={`mt-1 block max-w-[180px] truncate text-[11px] ${pull.ok ? "text-emerald-400" : "text-red-400"}`}
                                    title={pull.msg}
                                  >
                                    {pull.msg}
                                  </span>
                                )}
                              </>
                            ) : (
                              <span className="text-slate-600">—</span>
                            )}
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
                {table.rows.map((img) => {
                  const ref = imageRef(img);
                  const dangling = img.dangling || !img.repo_tags?.length;
                  const pull = pulls[ref];
                  const extraTags = (img.repo_tags || []).filter((t) => t !== ref);
                  return (
                    <div
                      key={img.id}
                      className="flex flex-col rounded-lg border border-slate-800 bg-slate-900/60 p-4 transition-colors hover:border-slate-700 hover:bg-slate-900"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <Link
                          to={resourceHref("images", ref)}
                          className="flex min-w-0 items-center gap-2 text-blue-400 hover:underline"
                        >
                          <ImageIcon className="h-4 w-4 shrink-0 text-blue-500" />
                          <span
                            className="truncate font-mono text-[13px] text-slate-100"
                            title={ref}
                          >
                            {truncate(ref || "<none>", 48)}
                          </span>
                        </Link>
                        <UsedBadge count={img.used_count} />
                      </div>
                      <p className="mt-2 text-xs leading-relaxed text-slate-400">
                        {truncate(describeImage(ref), 140)}
                      </p>
                      <div className="mt-2 flex flex-wrap items-center gap-1.5">
                        <KindBadge
                          kind={img.provenance?.kind}
                          fleetRepo={img.provenance?.fleet_repo}
                        />
                        {dangling && (
                          <span className="rounded-full border border-amber-800 bg-amber-950/60 px-2 py-0.5 text-[11px] text-amber-300">
                            dangling
                          </span>
                        )}
                        <span className="rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 font-mono text-[11px] text-slate-300">
                          {[img.os, img.architecture].filter(Boolean).join("/") || "—"}
                        </span>
                      </div>
                      <div className="mt-3 flex items-end justify-between gap-2">
                        <div>
                          <p className="text-[11px] uppercase tracking-wide text-slate-500">Size</p>
                          <p className="text-xl font-bold text-slate-100">
                            {formatBytes(img.size)}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-[11px] uppercase tracking-wide text-slate-500">Age</p>
                          <p className="font-medium text-slate-200" title={formatDate(img.created)}>
                            {formatAge(img.created)}
                          </p>
                        </div>
                      </div>
                      {extraTags.length > 0 && (
                        <p
                          className="mt-2 truncate font-mono text-[11px] text-slate-500"
                          title={extraTags.join("\n")}
                        >
                          +{extraTags.length} more tag{extraTags.length === 1 ? "" : "s"}
                        </p>
                      )}
                      {(img.used_by || []).length > 0 && (
                        <p
                          className="mt-1 truncate text-[11px] text-slate-500"
                          title={(img.used_by || []).join(", ")}
                        >
                          Used by: {(img.used_by || []).join(", ")}
                        </p>
                      )}
                      <div className="mt-3 flex items-center justify-between border-t border-slate-800 pt-3">
                        <Link
                          to={resourceHref("images", ref)}
                          className="text-[13px] font-medium text-blue-400 hover:underline"
                        >
                          View details →
                        </Link>
                        {!dangling && ref ? (
                          <span className="flex flex-col items-end">
                            <button
                              type="button"
                              disabled={pull?.busy}
                              onClick={() => void pullImage(ref)}
                              className="inline-flex items-center gap-1 rounded-md bg-slate-800 px-2 py-1 text-xs font-medium text-slate-200 hover:bg-slate-700 disabled:opacity-50"
                            >
                              {pull?.busy ? (
                                <Loader2 className="h-3 w-3 animate-spin" />
                              ) : (
                                <Download className="h-3 w-3" />
                              )}
                              Pull
                            </button>
                            {pull?.msg && (
                              <span
                                className={`mt-1 max-w-[180px] truncate text-[11px] ${pull.ok ? "text-emerald-400" : "text-red-400"}`}
                                title={pull.msg}
                              >
                                {pull.msg}
                              </span>
                            )}
                          </span>
                        ) : null}
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
