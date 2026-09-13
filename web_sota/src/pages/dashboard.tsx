import {
  Activity,
  AlertCircle,
  Archive,
  Box,
  Container,
  Cpu,
  Database,
  HardDrive,
  Image as ImageIcon,
  Layers,
  Loader2,
  type LucideIcon,
  MessageSquare,
  Network,
  RefreshCw,
  ScrollText,
  Stethoscope,
  Trash2,
  Wrench,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ToolsHarnessExplainer } from "@/components/tools-harness-explainer";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API_BASE } from "@/lib/api";
import { formatBytes, imageRef, resourceHref } from "@/lib/format";
import { useConnection } from "@/store/connection";

interface ContainerItem {
  id: string;
  name: string;
  status: string;
  image: string;
  state: string;
}

interface SystemInfo {
  docker_version?: string;
  containers?: { total?: number; running?: number; paused?: number; stopped?: number };
  images?: { total?: number };
  memory?: { total?: number; total_formatted?: string };
  cpu?: { cores?: number };
}

interface ImageItem {
  id?: string;
  repo_tags?: string[];
  size?: number;
  created?: string;
}

interface DashboardData {
  containers: ContainerItem[];
  containers_status?: string;
  containers_message?: string;
  system_info: SystemInfo | null;
  system_status?: string;
  disk_summary?: {
    total_containers_size?: number;
    total_images_size?: number;
    total_volumes_size?: number;
    total_size?: number;
  } | null;
  images: ImageItem[];
  images_count?: number;
  images_status?: string;
  images_size_estimate?: number;
  volumes_count?: number;
  networks_count?: number;
}

export function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const connState = useConnection((s) => s.state);
  const prevConn = useRef(connState);

  const fetchDashboard = useCallback(async (opts?: { silent?: boolean }) => {
    if (!opts?.silent) setLoading(true);
    try {
      const sysRes = await fetch(`${API_BASE}/api/system`);
      if (!sysRes.ok) throw new Error(`HTTP ${sysRes.status}`);
      const sysJson = await sysRes.json();
      const sysInfo = sysJson.system_info ?? sysJson;
      setData((prev) => ({
        containers: prev?.containers ?? [],
        images: prev?.images ?? [],
        disk_summary: prev?.disk_summary ?? null,
        images_count: prev?.images_count,
        images_size_estimate: prev?.images_size_estimate,
        system_info: sysInfo,
        system_status: sysJson.status ?? "success",
        containers_status: "success",
        containers_message: "Loading containers…",
      }));
      setError(null);
      setLoading(false);

      const [cRes, iRes, vRes, nRes] = await Promise.all([
        fetch(`${API_BASE}/api/containers?all=false`),
        fetch(`${API_BASE}/api/images`),
        fetch(`${API_BASE}/api/volumes`),
        fetch(`${API_BASE}/api/networks`),
      ]);
      const cJson = cRes.ok ? await cRes.json() : { containers: [], status: "error" };
      const iJson = iRes.ok ? await iRes.json() : { images: [], count: 0, status: "error" };
      const vJson = vRes.ok ? await vRes.json() : { count: 0 };
      const nJson = nRes.ok ? await nRes.json() : { count: 0 };
      const imageRows = iJson.images ?? [];
      const estimate = imageRows.reduce((sum: number, img: ImageItem) => sum + (img.size || 0), 0);
      const counts = sysInfo?.containers ?? {};
      const running = counts.running;
      const total = counts.total;
      setData((prev) => ({
        ...(prev ?? { system_info: sysInfo, containers: [], images: [] }),
        containers: cJson.containers ?? [],
        containers_status: cJson.status,
        containers_message:
          running != null && total != null ? `${running} running / ${total} total` : cJson.message,
        images: imageRows.slice(0, 12),
        images_count: iJson.count ?? imageRows.length,
        images_status: iJson.status,
        images_size_estimate: estimate,
        volumes_count: vJson.count ?? vJson.volumes?.length ?? 0,
        networks_count: nJson.count ?? nJson.networks?.length ?? 0,
        system_info: sysInfo,
        system_status: sysJson.status ?? "success",
      }));

      void fetch(`${API_BASE}/api/disk`)
        .then(async (diskRes) => {
          if (!diskRes.ok) return;
          const diskJson = await diskRes.json();
          const summary = diskJson?.disk_usage?.summary;
          if (summary) {
            setData((prev) => (prev ? { ...prev, disk_summary: summary } : prev));
          }
        })
        .catch(() => undefined);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load dashboard");
      setData(null);
      setLoading(false);
    }
  }, []);

  // Initial fetch on mount
  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  // Re-fetch when backend transitions to connected (e.g. after startup delay)
  useEffect(() => {
    if (prevConn.current !== "connected" && connState === "connected") {
      fetchDashboard({ silent: Boolean(data) });
    }
    prevConn.current = connState;
  }, [connState, fetchDashboard, data]);

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center min-h-[320px]">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-6" data-testid="dashboard-error">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Docker Dashboard</h2>
          <p className="text-slate-400">AI-powered Docker management via natural language</p>
        </div>
        <Card className="border-red-900/50 bg-red-950/20">
          <CardContent className="flex items-center gap-3 pt-6">
            <AlertCircle className="h-8 w-8 text-red-500 shrink-0" />
            <div className="flex-1">
              <p className="text-red-200">
                {error ?? "No data"} — Is the backend running and Docker available?
              </p>
            </div>
            <RestartDockerButton onRecovered={fetchDashboard} />
          </CardContent>
        </Card>
        <QuickActions onRecovered={fetchDashboard} />
      </div>
    );
  }

  const containers = data.containers ?? [];
  const sys = data.system_info ?? {};
  const counts = sys.containers ?? {};
  const running = counts.running ?? containers.filter((c) => c.state === "running").length;
  const stopped = counts.stopped ?? Math.max(0, (counts.total ?? containers.length) - running);
  const containerTotal = counts.total ?? containers.length;
  const mem = sys.memory ?? {};
  const disk = data.disk_summary ?? {};
  const totalSize = disk.total_size ?? data.images_size_estimate ?? 0;
  const images = data.images ?? [];
  const storageHint = data.disk_summary
    ? "Images, volumes, cache"
    : "Image sizes (df still running)";

  return (
    <div className="space-y-6" data-testid="dashboard-ready">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Docker Dashboard</h2>
          <p className="text-slate-400">Container overview and engine status</p>
        </div>
      </div>

      <div className="bg-gradient-to-br from-blue-900/20 via-slate-900/50 to-transparent border border-blue-900/30 rounded-xl px-6 py-5">
        <h3 className="text-lg font-semibold text-white">Docker MCP</h3>
        <p className="text-sm text-slate-300 mt-1">
          Browse containers and images in the sidebar, or run any MCP tool (backup, prune, diagnose,
          GPU, daemon) in the tool harness — the same operations agents call over MCP, without a
          separate page for each one.
        </p>
        <p className="text-xs text-slate-500 mt-1">
          Backend port 10807 · MCP endpoint /mcp · Fleet: mcp-central-docs/projects/docker-mcp
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Link
            to="/tools"
            data-testid="hero-cta-tools"
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500"
          >
            <Wrench className="h-4 w-4" />
            Run MCP tools
          </Link>
          <Link
            to="/chat"
            className="inline-flex items-center gap-2 rounded-md border border-slate-600 bg-slate-900/60 px-4 py-2 text-sm text-slate-200 hover:bg-slate-800"
          >
            <MessageSquare className="h-4 w-4" />
            AI Command
          </Link>
        </div>
      </div>

      <QuickActions onRecovered={fetchDashboard} />

      <ToolsHarnessExplainer variant="dashboard" />

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="border-slate-800 bg-slate-950/50">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-200">Containers</CardTitle>
            <Box className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">{containerTotal}</div>
            <p className="text-xs text-slate-400">
              {running} Running | {stopped} Stopped
            </p>
            <Link
              to="/containers"
              className="text-xs text-blue-400 hover:underline mt-1 inline-block"
            >
              View all
            </Link>
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-950/50">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-200">Volumes</CardTitle>
            <Database className="h-4 w-4 text-sky-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">{data.volumes_count ?? "—"}</div>
            <p className="text-xs text-slate-400">Named volumes</p>
            <Link to="/volumes" className="text-xs text-blue-400 hover:underline mt-1 inline-block">
              View all
            </Link>
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-950/50">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-200">Networks</CardTitle>
            <Network className="h-4 w-4 text-indigo-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">{data.networks_count ?? "—"}</div>
            <p className="text-xs text-slate-400">Docker networks</p>
            <Link
              to="/networks"
              className="text-xs text-blue-400 hover:underline mt-1 inline-block"
            >
              View all
            </Link>
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-950/50">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-200">CPU</CardTitle>
            <Cpu className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">{sys.cpu?.cores ?? "—"} cores</div>
            <p className="text-xs text-slate-400">Host</p>
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-950/50">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-200">Memory</CardTitle>
            <Activity className="h-4 w-4 text-purple-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">
              {mem.total_formatted ?? (mem.total != null ? formatBytes(mem.total) : "—")}
            </div>
            <p className="text-xs text-slate-400">Total</p>
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-950/50">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-200">Storage</CardTitle>
            <HardDrive className="h-4 w-4 text-orange-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">
              {totalSize > 0 ? formatBytes(totalSize) : "—"}
            </div>
            <p className="text-xs text-slate-400">{storageHint}</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <Card className="col-span-4 border-slate-800 bg-slate-950/50">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-white">Containers</CardTitle>
            <Link to="/containers" className="text-xs text-blue-400 hover:underline">
              View all
            </Link>
          </CardHeader>
          <CardContent>
            <div className="max-h-[240px] overflow-y-auto space-y-1">
              {containers.length === 0 ? (
                <p className="text-slate-500 text-sm">No containers</p>
              ) : (
                containers.slice(0, 12).map((c) => (
                  <Link
                    key={c.id}
                    to={resourceHref("containers", c.id)}
                    className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 hover:bg-slate-800/40"
                  >
                    <span className="flex items-center gap-2 min-w-0">
                      <Box className="h-4 w-4 text-blue-400 shrink-0" />
                      <span className="text-sm text-white truncate">{c.name}</span>
                    </span>
                    <span
                      className={
                        c.state === "running"
                          ? "text-xs text-emerald-400"
                          : "text-xs text-slate-500"
                      }
                    >
                      {c.state}
                    </span>
                  </Link>
                ))
              )}
            </div>
          </CardContent>
        </Card>
        <Card className="col-span-3 border-slate-800 bg-slate-950/50">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-white">
              Images ({data.images_count ?? images.length})
            </CardTitle>
            <Link to="/images" className="text-xs text-blue-400 hover:underline">
              View all
            </Link>
          </CardHeader>
          <CardContent>
            <div className="space-y-4 max-h-[200px] overflow-y-auto">
              {images.length === 0 ? (
                <p className="text-slate-500 text-sm">No images</p>
              ) : (
                images.slice(0, 8).map((img, i) => {
                  const tag = imageRef(img);
                  const sz = img.size != null ? formatBytes(img.size) : "";
                  return (
                    <Link
                      key={img.id || i}
                      to={resourceHref("images", tag || img.id || "")}
                      className="flex items-center hover:bg-slate-800/40 rounded-md px-1 py-1 -mx-1"
                    >
                      <Box className="h-4 w-4 text-blue-400 mr-2 shrink-0" />
                      <div className="min-w-0 space-y-0.5">
                        <p className="text-sm font-medium leading-none text-white truncate">
                          {tag || "—"}
                        </p>
                        {sz && <p className="text-xs text-slate-400">{sz}</p>}
                      </div>
                    </Link>
                  );
                })
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

const PAGE_ACTIONS: {
  to: string;
  label: string;
  hint: string;
  icon: LucideIcon;
  primary?: boolean;
  testId?: string;
}[] = [
  {
    to: "/tools",
    label: "MCP Tools",
    hint: "Tool harness (same as AI)",
    icon: Wrench,
    primary: true,
    testId: "quick-action-tools",
  },
  { to: "/chat", label: "AI Command", hint: "Natural language", icon: MessageSquare },
  { to: "/containers", label: "Containers", hint: "List and inspect", icon: Container },
  { to: "/images", label: "Images", hint: "Tags and sizes", icon: ImageIcon },
  { to: "/volumes", label: "Volumes", hint: "Named volumes", icon: Database },
  { to: "/networks", label: "Networks", hint: "Bridges and overlays", icon: Network },
  { to: "/compose", label: "Compose", hint: "Projects up/down", icon: Layers },
  { to: "/logs", label: "Event logs", hint: "API activity", icon: ScrollText },
];

const TOOL_SHORTCUTS: { to: string; label: string; hint: string; icon: LucideIcon }[] = [
  {
    to: "/tools/agentic_workflow?operation=diagnose",
    label: "Diagnose",
    hint: "agentic_workflow",
    icon: Stethoscope,
  },
  { to: "/tools/docker_backup", label: "Backup", hint: "Images and volumes", icon: Archive },
  { to: "/tools/prune_system", label: "Prune unused", hint: "Needs confirm", icon: Trash2 },
  {
    to: "/tools/get_docker_status_tool",
    label: "Daemon status",
    hint: "get_docker_status_tool",
    icon: Activity,
  },
];

function QuickActionLink({
  to,
  label,
  hint,
  icon: Icon,
  primary,
  testId,
}: {
  to: string;
  label: string;
  hint?: string;
  icon: LucideIcon;
  primary?: boolean;
  testId?: string;
}) {
  return (
    <Link
      to={to}
      data-testid={testId}
      className={
        primary
          ? "flex items-center gap-3 rounded-lg border border-blue-500/60 bg-blue-600 px-4 py-3 text-white hover:bg-blue-500"
          : "flex items-center gap-3 rounded-lg border border-slate-700 bg-slate-900/70 px-4 py-3 text-slate-200 hover:border-blue-500/40 hover:bg-slate-800 hover:text-white"
      }
    >
      <Icon className={`h-5 w-5 shrink-0 ${primary ? "text-white" : "text-blue-400"}`} />
      <span className="min-w-0">
        <span className="block text-sm font-medium">{label}</span>
        {hint ? (
          <span className={`block text-xs ${primary ? "text-blue-100" : "text-slate-400"}`}>
            {hint}
          </span>
        ) : null}
      </span>
    </Link>
  );
}

function QuickActions({ onRecovered }: { onRecovered?: () => void }) {
  return (
    <section className="space-y-3" data-testid="quick-actions">
      <div>
        <h3 className="text-sm font-medium uppercase tracking-wider text-slate-500">
          Quick actions
        </h3>
        <p className="text-xs text-slate-500 mt-1">
          Top row: browse pages. Second row: MCP tool shortcuts (harness forms, not duplicate REST
          pages).
        </p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {PAGE_ACTIONS.map((action) => (
          <QuickActionLink key={action.to} {...action} />
        ))}
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {TOOL_SHORTCUTS.map((action) => (
          <QuickActionLink key={action.to} {...action} />
        ))}
        <div className="flex items-stretch">
          <RestartDockerButton onRecovered={onRecovered} compact />
        </div>
      </div>
    </section>
  );
}

function RestartDockerButton({
  onRecovered,
  compact,
}: {
  onRecovered?: () => void;
  compact?: boolean;
}) {
  const [restarting, setRestarting] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const handleRestart = useCallback(async () => {
    setRestarting(true);
    setResult(null);
    try {
      const r = await fetch(`${API_BASE}/api/docker/recover`, { method: "POST" });
      const d = await r.json();
      if (d.success) {
        setResult("Docker connected");
        if (onRecovered) onRecovered();
      } else {
        setResult(d.message);
      }
    } catch {
      setResult("Failed to trigger restart");
    } finally {
      setRestarting(false);
    }
  }, [onRecovered]);
  if (compact) {
    return (
      <button
        type="button"
        onClick={handleRestart}
        disabled={restarting}
        data-testid="quick-action-recover"
        className="flex w-full items-center gap-3 rounded-lg border border-red-900/60 bg-red-950/40 px-4 py-3 text-left text-red-100 hover:bg-red-900/50 disabled:opacity-50"
      >
        <RefreshCw className={`h-5 w-5 shrink-0 ${restarting ? "animate-spin" : ""}`} />
        <span className="min-w-0">
          <span className="block text-sm font-medium">
            {restarting ? "Restarting…" : "Recover Docker"}
          </span>
          <span className="block text-xs text-red-300/80">{result ?? "Triple-kill Desktop"}</span>
        </span>
      </button>
    );
  }
  return (
    <div className="flex flex-col items-end gap-1">
      <button
        type="button"
        onClick={handleRestart}
        disabled={restarting}
        className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium bg-red-700 hover:bg-red-600 disabled:opacity-50 text-white rounded-md transition-colors"
      >
        <RefreshCw className={`h-4 w-4 ${restarting ? "animate-spin" : ""}`} />
        {restarting ? "Restarting..." : "Restart Docker"}
      </button>
      {result && <span className="text-xs text-slate-400">{result}</span>}
    </div>
  );
}
