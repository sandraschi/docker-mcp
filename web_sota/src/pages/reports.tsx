import { AlertCircle, Download, FileText, Loader2, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API_BASE } from "@/lib/api";
import { downloadFile, exportJSON } from "@/lib/export";
import { formatBytes, resourceHref, truncate } from "@/lib/format";

interface JunkItem {
  ref?: string;
  name?: string;
  id?: string;
  size?: number | null;
  age_days?: number | null;
  used_count?: number;
  kind?: string;
  fleet_repo?: string | null;
  reason?: string;
  driver?: string;
  subnet?: string;
}

interface ReportPayload {
  generatedAt: string;
  system: Record<string, unknown> | null;
  disk: Record<string, number> | null;
  counts: {
    containers: number | null;
    containersRunning: number | null;
    images: number | null;
    volumes: number | null;
    networks: number | null;
  };
  junkSummary: Record<string, number> | null;
  reclaimableBytes: number | null;
  groups: Record<string, JunkItem[]>;
}

function sysPath(obj: Record<string, unknown> | null, ...keys: string[]): string {
  let cur: unknown = obj;
  for (const k of keys) {
    if (cur == null || typeof cur !== "object") return "—";
    cur = (cur as Record<string, unknown>)[k];
  }
  if (cur == null) return "—";
  if (typeof cur === "object") return JSON.stringify(cur);
  return String(cur);
}

function buildMarkdown(r: ReportPayload): string {
  const lines: string[] = [];
  lines.push(`# Docker status report`);
  lines.push(``);
  lines.push(`Generated: ${r.generatedAt}`);
  lines.push(``);
  lines.push(`## Engine`);
  lines.push(``);
  lines.push(`- Docker version: ${sysPath(r.system, "system_info", "docker_version")}`);
  lines.push(`- API version: ${sysPath(r.system, "system_info", "api_version")}`);
  lines.push(
    `- OS / Arch: ${sysPath(r.system, "system_info", "operating_system")} / ${sysPath(r.system, "system_info", "architecture")}`,
  );
  lines.push(
    `- CPU / Memory: ${sysPath(r.system, "system_info", "cpu", "cores")} cores / ${sysPath(r.system, "system_info", "memory", "total_formatted")}`,
  );
  lines.push(``);
  lines.push(`## Counts`);
  lines.push(``);
  lines.push(`| Kind | Count |`);
  lines.push(`| --- | --- |`);
  lines.push(
    `| Containers (running / total) | ${r.counts.containersRunning ?? "—"} / ${r.counts.containers ?? "—"} |`,
  );
  lines.push(`| Images | ${r.counts.images ?? "—"} |`);
  lines.push(`| Volumes | ${r.counts.volumes ?? "—"} |`);
  lines.push(`| Networks | ${r.counts.networks ?? "—"} |`);
  lines.push(``);
  if (r.disk) {
    lines.push(`## Disk usage (docker system df)`);
    lines.push(``);
    lines.push(`| Area | Size |`);
    lines.push(`| --- | --- |`);
    for (const [k, v] of Object.entries(r.disk)) {
      lines.push(`| ${k} | ${formatBytes(v)} |`);
    }
    lines.push(``);
  }
  const j = r.junkSummary ?? {};
  lines.push(`## Cleanup opportunities`);
  lines.push(``);
  lines.push(
    `Reclaimable (gross, before shared layers): ${r.reclaimableBytes != null ? formatBytes(r.reclaimableBytes) : "—"}`,
  );
  lines.push(
    `Unused images: ${j.unused_images ?? 0}, dangling: ${j.dangling_images ?? 0}, unused volumes: ${j.unused_volumes ?? 0}, stopped containers: ${j.stopped_containers ?? 0}, unused networks: ${j.unused_networks ?? 0}, old images: ${j.old_images ?? 0}.`,
  );
  lines.push(``);
  const group = (title: string, key: string) => {
    const items = r.groups[key] ?? [];
    if (items.length === 0) return;
    lines.push(`### ${title} (${items.length})`);
    lines.push(``);
    for (const it of items.slice(0, 20)) {
      const label = it.ref || it.name || it.id || "?";
      const size = it.size != null ? ` — ${formatBytes(it.size)}` : "";
      lines.push(`- ${label}${size}${it.reason ? ` — ${it.reason}` : ""}`);
    }
    if (items.length > 20) lines.push(`- …and ${items.length - 20} more (see JSON export)`);
    lines.push(``);
  };
  group("Unused images", "unused_images");
  group("Dangling images", "dangling_images");
  group("Unused volumes", "unused_volumes");
  group("Old images (update candidates)", "old_images");
  group("Stopped containers", "stopped_containers");
  group("Unused networks", "unused_networks");
  return lines.join("\n");
}

export function Reports() {
  const [report, setReport] = useState<ReportPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchReport = useCallback(async (silent?: boolean) => {
    if (!silent) setLoading(true);
    try {
      const [sysRes, diskRes, dashRes, junkRes] = await Promise.all([
        fetch(`${API_BASE}/api/system`),
        fetch(`${API_BASE}/api/disk`),
        fetch(`${API_BASE}/api/dashboard`),
        fetch(`${API_BASE}/api/junk`),
      ]);
      const sys = sysRes.ok ? await sysRes.json() : null;
      const diskJson = diskRes.ok ? await diskRes.json() : null;
      const dash = dashRes.ok ? await dashRes.json() : null;
      const junk = junkRes.ok ? await junkRes.json() : null;
      const sysCounts = (sys?.system_info?.containers ?? {}) as Record<string, number>;
      const payload: ReportPayload = {
        generatedAt: new Date().toISOString(),
        system: sys,
        disk: (diskJson?.disk_usage?.summary ?? null) as Record<string, number> | null,
        counts: {
          containers: sysCounts.total ?? dash?.containers?.length ?? null,
          containersRunning: sysCounts.running ?? null,
          images: junk?.summary?.image_count ?? dash?.images_count ?? null,
          volumes: junk?.summary?.volume_count ?? null,
          networks: junk?.summary?.network_count ?? null,
        },
        junkSummary: (junk?.summary ?? null) as Record<string, number> | null,
        reclaimableBytes: junk?.summary?.reclaimable_bytes ?? null,
        groups: (junk?.groups ?? {}) as Record<string, JunkItem[]>,
      };
      setReport(payload);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to build report");
      setReport(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  if (loading && !report) {
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
          <h2 className="flex items-center gap-2 text-2xl font-bold tracking-tight text-white">
            <FileText className="h-6 w-6 text-blue-500" /> Status report
          </h2>
          <p className="text-slate-400">
            {report
              ? `Generated ${new Date(report.generatedAt).toLocaleString()}`
              : "Global Docker status with export"}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => void fetchReport()}
            disabled={loading}
            className="inline-flex items-center gap-1.5 rounded-md bg-slate-800 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            {loading ? "Refreshing…" : "Refresh"}
          </button>
          <button
            type="button"
            disabled={!report}
            onClick={() =>
              report &&
              downloadFile(
                `docker-status-report-${report.generatedAt.slice(0, 10)}.md`,
                buildMarkdown(report),
                "text/markdown",
              )
            }
            className="inline-flex items-center gap-1.5 rounded-md bg-slate-800 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700 disabled:opacity-50"
          >
            <Download className="h-4 w-4" /> Markdown
          </button>
          <button
            type="button"
            disabled={!report}
            onClick={() => report && exportJSON("docker-status-report", report)}
            className="inline-flex items-center gap-1.5 rounded-md bg-slate-800 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700 disabled:opacity-50"
          >
            <Download className="h-4 w-4" /> JSON
          </button>
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

      {report && (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
            <Stat
              label="Containers"
              value={`${report.counts.containersRunning ?? "—"} / ${report.counts.containers ?? "—"}`}
              sub="running / total"
              to="/containers"
            />
            <Stat
              label="Images"
              value={String(report.counts.images ?? "—")}
              sub="total"
              to="/images"
            />
            <Stat
              label="Volumes"
              value={String(report.counts.volumes ?? "—")}
              sub="total"
              to="/volumes"
            />
            <Stat
              label="Networks"
              value={String(report.counts.networks ?? "—")}
              sub="total"
              to="/networks"
            />
            <Stat
              label="Reclaimable"
              value={report.reclaimableBytes != null ? formatBytes(report.reclaimableBytes) : "—"}
              sub="gross, pre-sharing"
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="border-slate-800 bg-slate-950/50">
              <CardHeader>
                <CardTitle className="text-white">Engine</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1 text-sm text-slate-300">
                <p>
                  Docker {sysPath(report.system, "system_info", "docker_version")} · API{" "}
                  {sysPath(report.system, "system_info", "api_version")}
                </p>
                <p className="text-slate-400">
                  {sysPath(report.system, "system_info", "operating_system")} /{" "}
                  {sysPath(report.system, "system_info", "architecture")} ·{" "}
                  {sysPath(report.system, "system_info", "cpu", "cores")} cores ·{" "}
                  {sysPath(report.system, "system_info", "memory", "total_formatted")}
                </p>
              </CardContent>
            </Card>
            <Card className="border-slate-800 bg-slate-950/50">
              <CardHeader>
                <CardTitle className="text-white">Disk usage</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1 text-sm text-slate-300">
                {report.disk ? (
                  Object.entries(report.disk).map(([k, v]) => (
                    <p key={k} className="flex justify-between gap-2">
                      <span className="text-slate-400">{k}</span>
                      <span className="font-mono">{formatBytes(v)}</span>
                    </p>
                  ))
                ) : (
                  <p className="text-slate-500">
                    Disk info unavailable (df still running or failed).
                  </p>
                )}
              </CardContent>
            </Card>
          </div>

          <CleanupGroup
            title="Unused images"
            items={report.groups.unused_images ?? []}
            render={(it) => (
              <Link
                to={resourceHref("images", it.ref || it.id || "")}
                className="text-blue-400 hover:underline"
              >
                {truncate(it.ref || it.id || "?", 56)}
              </Link>
            )}
          />
          <CleanupGroup
            title="Unused volumes"
            items={report.groups.unused_volumes ?? []}
            render={(it) => (
              <Link
                to={resourceHref("volumes", it.name || "")}
                className="text-blue-400 hover:underline"
              >
                {truncate(it.name || "?", 56)}
              </Link>
            )}
          />
          <CleanupGroup
            title="Old images — update candidates"
            items={report.groups.old_images ?? []}
            render={(it) => (
              <Link
                to={resourceHref("images", it.ref || it.id || "")}
                className="text-blue-400 hover:underline"
              >
                {truncate(it.ref || it.id || "?", 56)}
              </Link>
            )}
          />
          <CleanupGroup
            title="Dangling images"
            items={report.groups.dangling_images ?? []}
            render={(it) => <span className="font-mono text-xs">{truncate(it.id || "?", 24)}</span>}
          />
          <CleanupGroup
            title="Stopped containers"
            items={report.groups.stopped_containers ?? []}
            render={(it) => (
              <Link
                to={resourceHref("containers", it.id || "")}
                className="text-blue-400 hover:underline"
              >
                {truncate(it.name || it.id || "?", 48)}
              </Link>
            )}
          />
          <CleanupGroup
            title="Unused networks"
            items={report.groups.unused_networks ?? []}
            render={(it) => (
              <Link
                to={resourceHref("networks", it.id || "")}
                className="text-blue-400 hover:underline"
              >
                {truncate(it.name || it.id || "?", 48)}
              </Link>
            )}
          />
        </>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  sub,
  to,
}: {
  label: string;
  value: string;
  sub: string;
  to?: string;
}) {
  const inner = (
    <>
      <p className="text-xs text-slate-400">{label}</p>
      <p className="text-lg font-semibold text-white">{value}</p>
      <p className="text-[11px] text-slate-500">{sub}</p>
    </>
  );
  return (
    <Card className="border-slate-800 bg-slate-950/50">
      <CardContent className="pt-4">
        {to ? (
          <Link to={to} className="block hover:opacity-80">
            {inner}
          </Link>
        ) : (
          inner
        )}
      </CardContent>
    </Card>
  );
}

function CleanupGroup({
  title,
  items,
  render,
}: {
  title: string;
  items: JunkItem[];
  render: (it: JunkItem) => React.ReactNode;
}) {
  if (items.length === 0) return null;
  const shown = items.slice(0, 8);
  return (
    <Card className="border-slate-800 bg-slate-950/50">
      <CardHeader>
        <CardTitle className="text-white">
          {title} ({items.length})
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-left text-xs uppercase tracking-wide text-slate-400">
                <th className="px-3 py-2 font-medium">Item</th>
                <th className="px-3 py-2 font-medium">Size</th>
                <th className="px-3 py-2 font-medium">Detail</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {shown.map((it, i) => (
                <tr key={`${it.id || it.name || it.ref}-${i}`} className="text-slate-200">
                  <td className="max-w-[320px] px-3 py-2">{render(it)}</td>
                  <td className="whitespace-nowrap px-3 py-2 font-medium">
                    {it.size != null ? (
                      formatBytes(it.size)
                    ) : (
                      <span className="text-slate-600">—</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-xs text-slate-400">
                    {[it.reason, it.age_days != null ? `${it.age_days}d old` : null]
                      .filter(Boolean)
                      .join(" · ")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {items.length > shown.length && (
          <p className="pt-3 text-xs text-slate-500">
            Showing {shown.length} of {items.length} — full list in the JSON export.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
