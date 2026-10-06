import {
  ArrowDown,
  ArrowUp,
  Container,
  Database,
  Eye,
  EyeOff,
  FileText,
  Layers,
  ListOrdered,
  Network,
  Play,
  RefreshCw,
  Server,
  Square,
  Terminal,
  Upload,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { analyzeComposeFile } from "@/common/api";
import { ExportButtons } from "@/components/export-buttons";
import { useViewMode, ViewToggle } from "@/components/view-toggle";
import { API_BASE } from "@/lib/api";
import type { Column } from "@/lib/export";
import { formatAge, formatBytes, truncate } from "@/lib/format";
import { PAGE_SIZES, type SortDir, useClientTable } from "@/lib/useClientTable";

interface ComposeProject {
  Name?: string;
  name?: string;
  Status?: string;
  status?: string;
  ConfigFiles?: string;
  configFiles?: string;
}

interface ComposeContainer {
  Name?: string;
  name?: string;
  Service?: string;
  service?: string;
  State?: string;
  state?: string;
  Status?: string;
  status?: string;
  Ports?: string;
  ports?: string;
  ID?: string;
  Id?: string;
  id?: string;
}

interface ComposeAnalysis {
  success: boolean;
  file_path?: string;
  file_size?: number;
  compose_version?: string;
  service_count?: number;
  volume_count?: number;
  network_count?: number;
  services?: Array<{
    name: string;
    image: string;
    build: string;
    ports: Array<{ host: string; container: string }>;
    volumes: string[];
    depends_on: string[];
    environment_keys: string[];
    restart: string;
    healthcheck: boolean;
    container_name: string;
  }>;
  volumes?: Array<{ name: string; driver: string }>;
  networks?: Array<{ name: string; driver: string }>;
  all_images?: string[];
  all_ports?: string[];
  has_build_contexts?: boolean;
  has_healthchecks?: boolean;
  has_depends_on?: boolean;
  unreferenced_volumes?: string[];
  error?: string;
}

const API = `${API_BASE}/api`;

interface ComposeFile {
  repo: string;
  path: string;
  name: string;
  size?: number;
  modified?: string;
  project_guess?: string;
  services?: number | null;
}

const FILE_COLUMNS: Array<Column<ComposeFile>> = [
  { key: "repo", label: "Repo", value: (f) => f.repo },
  { key: "project", label: "Project", value: (f) => f.project_guess },
  { key: "file", label: "File", value: (f) => f.name },
  { key: "path", label: "Path", value: (f) => f.path },
  { key: "services", label: "Services", value: (f) => f.services },
  { key: "size", label: "SizeBytes", value: (f) => f.size },
  { key: "modified", label: "Modified", value: (f) => f.modified },
];

const matchComposeFile = (f: ComposeFile, q: string) => {
  const hay = [f.repo, f.project_guess, f.name, f.path].filter(Boolean).join(" ").toLowerCase();
  return hay.includes(q);
};

const fileSortValue = (f: ComposeFile, key: string): string | number => {
  switch (key) {
    case "repo":
      return f.repo || "";
    case "project":
      return f.project_guess || "";
    case "services":
      return f.services ?? -1;
    case "size":
      return f.size ?? -1;
    case "modified":
      return f.modified || "";
    default:
      return f.repo || "";
  }
};

export function Compose() {
  const [projects, setProjects] = useState<ComposeProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedProject, setSelectedProject] = useState<string | null>(null);
  const [containers, setContainers] = useState<ComposeContainer[]>([]);
  const [logs, setLogs] = useState("");
  const [config, setConfig] = useState("");
  const [showConfig, setShowConfig] = useState(false);
  const [actionMsg, setActionMsg] = useState("");
  const [analysis, setAnalysis] = useState<ComposeAnalysis | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisPath, setAnalysisPath] = useState("");
  const [analysisError, setAnalysisError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [composeFiles, setComposeFiles] = useState<ComposeFile[]>([]);
  const [filesLoading, setFilesLoading] = useState(true);
  const [filesError, setFilesError] = useState<string | null>(null);
  const [filesRoot, setFilesRoot] = useState("");
  const [filesSearch, setFilesSearch] = useState("");
  const [filesSortKey, setFilesSortKey] = useState("repo");
  const [filesSortDir, setFilesSortDir] = useState<SortDir>("asc");
  const [filesPage, setFilesPage] = useState(0);
  const [filesPageSize, setFilesPageSize] = useState(50);
  const [filesView, setFilesView] = useViewMode("docker-mcp:compose-files:view", "list");
  const [fileBusy, setFileBusy] = useState<Record<string, string>>({});

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/compose/projects?all=true`);
      const data = await r.json();
      setProjects(data.projects ?? []);
    } catch {
      setProjects([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchComposeFiles = useCallback(async (force?: boolean) => {
    setFilesLoading(true);
    try {
      const r = await fetch(`${API}/compose/files${force ? "?refresh=true" : ""}`);
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
      setComposeFiles(data.files ?? []);
      setFilesRoot(data.root ?? "");
      setFilesError(data.warning ?? null);
    } catch (e) {
      setComposeFiles([]);
      setFilesError(e instanceof Error ? e.message : "Failed to scan compose files");
    } finally {
      setFilesLoading(false);
    }
  }, []);

  const runningProjectNames = useMemo(() => {
    const names = new Set<string>();
    for (const p of projects) {
      const name = p.Name ?? p.name ?? "";
      const status = (p.Status ?? p.status ?? "").toLowerCase();
      if (name && (status.includes("running") || status.includes("up")))
        names.add(name.toLowerCase());
    }
    return names;
  }, [projects]);

  const runAnalyze = useCallback(async (path: string) => {
    setAnalysisLoading(true);
    setAnalysisError("");
    try {
      const r = await fetch(`${API}/compose/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_path: path }),
      });
      const data = await r.json();
      setAnalysis(data);
      if (!data.success) setAnalysisError(data.error ?? "Analysis failed");
    } catch (err: unknown) {
      setAnalysisError(err instanceof Error ? err.message : "Analysis failed");
    }
    setAnalysisLoading(false);
  }, []);

  const analyzeFile = useCallback(
    (path: string) => {
      setAnalysisPath(path);
      setAnalysisError("");
      void runAnalyze(path);
      document.getElementById("compose-analyze")?.scrollIntoView({ behavior: "smooth" });
    },
    [runAnalyze],
  );

  const fileAction = useCallback(
    async (file: ComposeFile, action: "up" | "down") => {
      if (
        action === "down" &&
        !window.confirm(
          `Stop compose project '${file.project_guess}'? Containers will be removed (volumes kept).`,
        )
      ) {
        return;
      }
      setFileBusy((m) => ({ ...m, [file.path]: action }));
      setActionMsg(`${action === "up" ? "Starting" : "Stopping"} ${file.project_guess}...`);
      try {
        const dir = file.path.slice(
          0,
          Math.max(file.path.lastIndexOf("/"), file.path.lastIndexOf("\\")),
        );
        const r = await fetch(`${API}/compose/${action}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ project: file.project_guess, project_dir: dir }),
        });
        const data = await r.json();
        if (!data.success) throw new Error(data.error || data.message || `${action} failed`);
        setActionMsg(data.message ?? `${action} completed`);
        setTimeout(() => setActionMsg(""), 4000);
        fetchProjects();
      } catch (e: unknown) {
        setActionMsg(`Error: ${e instanceof Error ? e.message : action}`);
      } finally {
        setFileBusy((m) => {
          const next = { ...m };
          delete next[file.path];
          return next;
        });
      }
    },
    [fetchProjects],
  );

  const fetchContainers = useCallback(async (project: string) => {
    try {
      const r = await fetch(`${API}/compose/ps?project=${encodeURIComponent(project)}`);
      const data = await r.json();
      setContainers(data.containers ?? []);
    } catch {
      setContainers([]);
    }
  }, []);

  const fetchLogs = useCallback(async (project: string) => {
    try {
      const r = await fetch(`${API}/compose/logs?project=${encodeURIComponent(project)}&tail=50`);
      const data = await r.json();
      setLogs(data.output ?? data.logs ?? "");
    } catch {
      setLogs("(failed to fetch logs)");
    }
  }, []);

  const fetchConfig = useCallback(async (project: string) => {
    try {
      const r = await fetch(`${API}/compose/config?project=${encodeURIComponent(project)}`);
      const data = await r.json();
      setConfig(data.config ?? "(no config)");
    } catch {
      setConfig("(failed to fetch config)");
    }
  }, []);

  const selectProject = useCallback(
    (name: string) => {
      setSelectedProject(name);
      setShowConfig(false);
      setLogs("");
      fetchContainers(name);
      fetchLogs(name);
    },
    [fetchContainers, fetchLogs],
  );

  const doAction = useCallback(
    async (action: "up" | "down", project: string) => {
      setActionMsg(`${action === "up" ? "Starting" : "Stopping"} ${project}...`);
      try {
        const r = await fetch(`${API}/compose/${action}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ project }),
        });
        const data = await r.json();
        setActionMsg(data.message ?? `${action} completed`);
        setTimeout(() => setActionMsg(""), 3000);
        fetchContainers(project);
        fetchProjects();
      } catch (e: any) {
        setActionMsg(`Error: ${e.message}`);
      }
    },
    [fetchContainers, fetchProjects],
  );

  const pickFile = useCallback(async () => {
    setAnalysisError("");
    try {
      const { open } = await import("@tauri-apps/plugin-dialog");
      const selected = await open({
        multiple: false,
        filters: [{ name: "Compose", extensions: ["yml", "yaml"] }],
      });
      if (selected) {
        setAnalysisPath(selected);
        setAnalysisLoading(true);
        const r = await analyzeComposeFile(selected);
        setAnalysis(r);
        if (!r.success) setAnalysisError(r.error ?? "Analysis failed");
        setAnalysisLoading(false);
      }
    } catch {
      // Not in Tauri — fall back to manual input
      if (fileInputRef.current) fileInputRef.current.click();
    }
  }, []);

  const handleFileInput = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setAnalysisPath(file.name);
    setAnalysisLoading(true);
    setAnalysisError("");
    const reader = new FileReader();
    reader.onload = async () => {
      // Send file content to backend for parsing
      try {
        const r = await fetch(`${API}/compose/analyze`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ file_path: `upload:${file.name}`, content: reader.result }),
        });
        const data = await r.json();
        setAnalysis(data);
        if (!data.success) setAnalysisError(data.error ?? "Analysis failed");
      } catch (err: any) {
        setAnalysisError(err.message);
      }
      setAnalysisLoading(false);
    };
    reader.readAsText(file);
  }, []);

  const analyzePath = useCallback(async () => {
    if (!analysisPath.trim()) return;
    await runAnalyze(analysisPath.trim());
  }, [analysisPath, runAnalyze]);

  const filesTable = useClientTable(composeFiles, {
    search: filesSearch,
    match: matchComposeFile,
    sortKey: filesSortKey,
    sortDir: filesSortDir,
    sortValue: fileSortValue,
    page: filesPage,
    pageSize: filesPageSize,
  });

  useEffect(() => {
    setFilesPage(0);
  }, [filesSearch, filesPageSize, filesView]);

  const toggleFilesSort = (key: string) => {
    if (filesSortKey === key) setFilesSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setFilesSortKey(key);
      setFilesSortDir(key === "modified" || key === "size" ? "desc" : "asc");
    }
  };

  useEffect(() => {
    fetchProjects();
    fetchComposeFiles();
  }, [fetchProjects, fetchComposeFiles]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Layers className="h-6 w-6 text-blue-400" />
          <h2 className="text-2xl font-bold tracking-tight text-white">Compose</h2>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => fetchProjects()}
            className="p-1.5 rounded-md text-slate-400 hover:text-white hover:bg-slate-800"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </button>
          {actionMsg && <span className="text-xs text-blue-400">{actionMsg}</span>}
        </div>
      </div>

      <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-slate-400" />
            <span className="text-sm font-medium text-slate-300">
              Compose files in repos ({filesTable.filteredCount} of {composeFiles.length})
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <ViewToggle mode={filesView} onChange={setFilesView} />
            <ExportButtons
              base="compose-files"
              columns={FILE_COLUMNS}
              rows={filesTable.sortedFull}
            />
            <button
              type="button"
              onClick={() => {
                fetchComposeFiles(true);
                fetchProjects();
              }}
              className="p-1.5 rounded-md text-slate-400 hover:text-white hover:bg-slate-800"
              title="Rescan repos"
            >
              <RefreshCw className={`h-4 w-4 ${filesLoading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>
        {filesRoot && (
          <p className="text-xs text-slate-500 font-mono truncate" title={filesRoot}>
            {filesRoot}
          </p>
        )}
        <div className="flex flex-wrap gap-2">
          <input
            value={filesSearch}
            onChange={(e) => setFilesSearch(e.target.value)}
            placeholder="Filter repo, project, file, path…"
            className="max-w-sm flex-1 min-w-[200px] bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200 placeholder-slate-600"
          />
          <select
            value={filesPageSize}
            onChange={(e) => setFilesPageSize(Number(e.target.value))}
            className="rounded-md border border-slate-700 bg-slate-800 px-2 py-1.5 text-xs text-slate-200"
          >
            {PAGE_SIZES.map((n) => (
              <option key={n} value={n}>
                {n} / page
              </option>
            ))}
          </select>
        </div>
        {filesError && <p className="text-xs text-amber-400">{filesError}</p>}
        {filesLoading && composeFiles.length === 0 ? (
          <p className="text-sm text-slate-500">Scanning repos for compose files…</p>
        ) : filesTable.rows.length === 0 ? (
          <p className="text-sm text-slate-500">No compose files match.</p>
        ) : filesView === "list" ? (
          <div className="overflow-x-auto rounded-md border border-slate-800/60">
            <table className="w-full min-w-[880px] text-sm">
              <thead className="bg-slate-900/80">
                <tr className="text-left text-xs uppercase tracking-wide text-slate-400">
                  <FilesSortTh
                    label="Repo / File"
                    k="repo"
                    sortKey={filesSortKey}
                    sortDir={filesSortDir}
                    onClick={toggleFilesSort}
                  />
                  <FilesSortTh
                    label="Project"
                    k="project"
                    sortKey={filesSortKey}
                    sortDir={filesSortDir}
                    onClick={toggleFilesSort}
                  />
                  <FilesSortTh
                    label="Services"
                    k="services"
                    sortKey={filesSortKey}
                    sortDir={filesSortDir}
                    onClick={toggleFilesSort}
                  />
                  <FilesSortTh
                    label="Modified"
                    k="modified"
                    sortKey={filesSortKey}
                    sortDir={filesSortDir}
                    onClick={toggleFilesSort}
                  />
                  <th className="px-3 py-2 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {filesTable.rows.map((f) => {
                  const running = runningProjectNames.has((f.project_guess || "").toLowerCase());
                  const busy = fileBusy[f.path];
                  return (
                    <tr key={f.path} className="text-slate-200 hover:bg-slate-800/40">
                      <td className="max-w-[320px] px-3 py-2 align-top">
                        <span className="mr-1.5 inline-flex items-center rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 text-[11px] text-slate-300">
                          {truncate(f.repo, 24)}
                        </span>
                        <span className="font-mono text-xs" title={f.path}>
                          {truncate(f.name, 32)}
                        </span>
                        <span
                          className="block truncate font-mono text-[11px] text-slate-500"
                          title={f.path}
                        >
                          {truncate(f.path, 72)}
                        </span>
                      </td>
                      <td className="px-3 py-2 align-top">
                        <span className="font-medium">{f.project_guess}</span>
                        {running && (
                          <span className="ml-1.5 inline-flex items-center gap-1 rounded-full border border-emerald-800 bg-emerald-950/60 px-2 py-0.5 text-[11px] text-emerald-300">
                            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                            running
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2 align-top text-center">
                        {f.services ?? <span className="text-slate-600">—</span>}
                      </td>
                      <td className="whitespace-nowrap px-3 py-2 align-top text-xs text-slate-400">
                        {formatAge(f.modified)}
                        {f.size != null && (
                          <span className="block text-[11px] text-slate-600">
                            {formatBytes(f.size)}
                          </span>
                        )}
                      </td>
                      <td className="whitespace-nowrap px-3 py-2 align-top">
                        <span className="inline-flex flex-wrap gap-1">
                          <button
                            type="button"
                            onClick={() => analyzeFile(f.path)}
                            className="rounded-md bg-slate-800 px-2 py-1 text-[11px] font-medium text-slate-200 hover:bg-slate-700"
                          >
                            Analyze
                          </button>
                          <button
                            type="button"
                            disabled={Boolean(busy)}
                            onClick={() => void fileAction(f, "up")}
                            className="rounded-md bg-emerald-800 px-2 py-1 text-[11px] font-medium text-emerald-100 hover:bg-emerald-700 disabled:opacity-50"
                          >
                            {busy === "up" ? "Starting…" : "Up"}
                          </button>
                          <button
                            type="button"
                            disabled={Boolean(busy)}
                            onClick={() => void fileAction(f, "down")}
                            className="rounded-md bg-red-800 px-2 py-1 text-[11px] font-medium text-red-100 hover:bg-red-700 disabled:opacity-50"
                          >
                            {busy === "down" ? "Stopping…" : "Down"}
                          </button>
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            {filesTable.rows.map((f) => {
              const running = runningProjectNames.has((f.project_guess || "").toLowerCase());
              const busy = fileBusy[f.path];
              return (
                <div
                  key={f.path}
                  className="flex flex-col rounded-lg border border-slate-800 bg-slate-900/60 p-3 transition-colors hover:border-slate-700"
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="truncate font-medium text-slate-100" title={f.project_guess}>
                      {truncate(f.project_guess || "?", 32)}
                    </span>
                    {running ? (
                      <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-emerald-800 bg-emerald-950/60 px-2 py-0.5 text-[11px] text-emerald-300">
                        <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                        running
                      </span>
                    ) : (
                      <span className="shrink-0 rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 text-[11px] text-slate-400">
                        {f.services ?? "?"} services
                      </span>
                    )}
                  </div>
                  <p className="mt-1 truncate font-mono text-[11px] text-slate-500" title={f.path}>
                    {f.repo}/{f.name}
                  </p>
                  <p className="mt-2 text-[11px] text-slate-500">
                    Modified {formatAge(f.modified)}
                    {f.size != null ? ` · ${formatBytes(f.size)}` : ""}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1 border-t border-slate-800 pt-2">
                    <button
                      type="button"
                      onClick={() => analyzeFile(f.path)}
                      className="rounded-md bg-slate-800 px-2 py-1 text-[11px] font-medium text-slate-200 hover:bg-slate-700"
                    >
                      Analyze
                    </button>
                    <button
                      type="button"
                      disabled={Boolean(busy)}
                      onClick={() => void fileAction(f, "up")}
                      className="rounded-md bg-emerald-800 px-2 py-1 text-[11px] font-medium text-emerald-100 hover:bg-emerald-700 disabled:opacity-50"
                    >
                      {busy === "up" ? "Starting…" : "Up"}
                    </button>
                    <button
                      type="button"
                      disabled={Boolean(busy)}
                      onClick={() => void fileAction(f, "down")}
                      className="rounded-md bg-red-800 px-2 py-1 text-[11px] font-medium text-red-100 hover:bg-red-700 disabled:opacity-50"
                    >
                      {busy === "down" ? "Stopping…" : "Down"}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
        {filesTable.pageCount > 1 && (
          <div className="flex items-center justify-between pt-1 text-xs text-slate-400">
            <span>
              Page {filesTable.page + 1} of {filesTable.pageCount}
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={filesTable.page <= 0}
                onClick={() => setFilesPage(filesTable.page - 1)}
                className="rounded-md bg-slate-800 px-3 py-1.5 disabled:opacity-40"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={filesTable.page >= filesTable.pageCount - 1}
                onClick={() => setFilesPage(filesTable.page + 1)}
                className="rounded-md bg-slate-800 px-3 py-1.5 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      <div
        id="compose-analyze"
        className="bg-slate-900/60 border border-slate-800 rounded-lg p-4 space-y-3"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-slate-400" />
            <span className="text-sm font-medium text-slate-300">Analyze Compose File</span>
          </div>
          <button
            type="button"
            onClick={pickFile}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md bg-blue-600/20 text-blue-400 hover:bg-blue-600/40 border border-blue-700/30"
          >
            <Upload className="h-3.5 w-3.5" /> Pick File
          </button>
        </div>
        <div className="flex gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept=".yml,.yaml"
            className="hidden"
            onChange={handleFileInput}
          />
          <input
            value={analysisPath}
            onChange={(e) => setAnalysisPath(e.target.value)}
            placeholder="Path to docker-compose.yml (or pick above)"
            className="flex-1 bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200 font-mono placeholder-slate-600"
          />
          <button
            type="button"
            onClick={analyzePath}
            disabled={analysisLoading || !analysisPath.trim()}
            className="px-3 py-1.5 text-xs rounded-md bg-slate-800 text-slate-300 hover:bg-slate-700 disabled:opacity-40 border border-slate-700"
          >
            {analysisLoading ? "..." : "Analyze"}
          </button>
        </div>
        {analysisError && <p className="text-xs text-red-400">{analysisError}</p>}
        {analysis && analysis.success && (
          <div className="border-t border-slate-800 pt-3 space-y-3">
            <div className="flex flex-wrap gap-2 text-xs">
              <span className="bg-slate-800 px-2 py-0.5 rounded text-slate-300">
                <Server className="h-3 w-3 inline mr-1" />
                {analysis.service_count} services
              </span>
              <span className="bg-slate-800 px-2 py-0.5 rounded text-slate-300">
                <Container className="h-3 w-3 inline mr-1" />
                {analysis.all_images?.length} images
              </span>
              <span className="bg-slate-800 px-2 py-0.5 rounded text-slate-300">
                <Database className="h-3 w-3 inline mr-1" />
                {analysis.volume_count} volumes
              </span>
              <span className="bg-slate-800 px-2 py-0.5 rounded text-slate-300">
                <Network className="h-3 w-3 inline mr-1" />
                {analysis.network_count} networks
              </span>
              <span className="bg-slate-800 px-2 py-0.5 rounded text-slate-300">
                <ListOrdered className="h-3 w-3 inline mr-1" />
                {analysis.all_ports?.length} ports
              </span>
              {analysis.has_healthchecks && (
                <span className="bg-emerald-900/40 px-2 py-0.5 rounded text-emerald-400">
                  healthchecks
                </span>
              )}
              {analysis.has_depends_on && (
                <span className="bg-amber-900/40 px-2 py-0.5 rounded text-amber-400">
                  depends-on
                </span>
              )}
              {analysis.has_build_contexts && (
                <span className="bg-amber-900/40 px-2 py-0.5 rounded text-amber-400">
                  build contexts
                </span>
              )}
            </div>
            {analysis.services && (
              <div className="space-y-1">
                {analysis.services.map((svc) => (
                  <div key={svc.name} className="bg-slate-800/50 rounded px-3 py-2 text-xs">
                    <div className="flex items-center justify-between text-slate-200 font-medium">
                      <span>{svc.name}</span>
                      {svc.image && <span className="text-slate-400 font-mono">{svc.image}</span>}
                      {svc.build && (
                        <span className="text-slate-400 font-mono">build: {svc.build}</span>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-2 mt-1 text-slate-500">
                      {svc.ports.length > 0 && (
                        <span>
                          ports: {svc.ports.map((p) => `${p.host}:${p.container}`).join(", ")}
                        </span>
                      )}
                      {svc.volumes.length > 0 && <span>volumes: {svc.volumes.join(", ")}</span>}
                      {svc.depends_on.length > 0 && (
                        <span>depends: {svc.depends_on.join(", ")}</span>
                      )}
                      {svc.restart && <span>restart: {svc.restart}</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="xl:col-span-1 space-y-2">
          <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider">Projects</h3>
          {projects.length === 0 ? (
            <p className="text-sm text-slate-500">No compose projects found.</p>
          ) : (
            <div className="space-y-1">
              {projects.map((p) => {
                const name = p.Name ?? p.name ?? "?";
                const status = (p.Status ?? p.status ?? "").toLowerCase();
                const running = status.includes("running") || status.includes("up");
                return (
                  <button
                    key={name}
                    type="button"
                    onClick={() => selectProject(name)}
                    className={`w-full text-left flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${selectedProject === name ? "bg-blue-600/20 border border-blue-500/30" : "bg-slate-900/60 border border-slate-800 hover:bg-slate-800/80"}`}
                  >
                    <span
                      className={`h-2 w-2 rounded-full shrink-0 ${running ? "bg-green-500" : "bg-slate-500"}`}
                    />
                    <span className="text-slate-200 font-medium">{name}</span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <div className="xl:col-span-2 space-y-4">
          {selectedProject ? (
            <>
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider">
                  {selectedProject}
                </h3>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => doAction("up", selectedProject)}
                    className="flex items-center gap-1 px-3 py-1.5 text-xs rounded-md bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600/40 border border-emerald-700/30"
                  >
                    <Play className="h-3.5 w-3.5" /> Up
                  </button>
                  <button
                    type="button"
                    onClick={() => doAction("down", selectedProject)}
                    className="flex items-center gap-1 px-3 py-1.5 text-xs rounded-md bg-red-600/20 text-red-400 hover:bg-red-600/40 border border-red-700/30"
                  >
                    <Square className="h-3.5 w-3.5" /> Down
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowConfig(!showConfig);
                      if (!showConfig) fetchConfig(selectedProject);
                    }}
                    className={`p-1.5 rounded-md ${showConfig ? "bg-blue-600/30 text-blue-400" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}
                  >
                    {showConfig ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              {showConfig && (
                <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-3">
                  <pre className="text-xs text-slate-300 font-mono whitespace-pre-wrap max-h-96 overflow-y-auto">
                    {config}
                  </pre>
                </div>
              )}

              <div className="bg-slate-900/60 border border-slate-800 rounded-lg overflow-hidden">
                <div className="px-3 py-2 border-b border-slate-800 text-xs text-slate-500 font-medium">
                  Containers
                </div>
                {containers.length === 0 ? (
                  <div className="px-3 py-4 text-sm text-slate-500">
                    No containers in this project.
                  </div>
                ) : (
                  <div className="divide-y divide-slate-800/50">
                    {containers.map((c, i) => {
                      const name = c.Name ?? c.name ?? "?";
                      const svc = c.Service ?? c.service ?? "?";
                      const state = (c.State ?? c.state ?? "").toLowerCase();
                      const status = c.Status ?? c.status ?? "";
                      const running = state === "running";
                      const cid = c.ID ?? c.Id ?? c.id;
                      return (
                        <div key={i} className="flex items-center gap-3 px-3 py-2 text-sm">
                          <span
                            className={`h-2 w-2 rounded-full shrink-0 ${running ? "bg-green-500" : "bg-red-500"}`}
                          />
                          {cid ? (
                            <Link
                              to={`/containers/${encodeURIComponent(cid)}`}
                              className="text-blue-400 hover:underline font-mono text-xs truncate max-w-[200px]"
                            >
                              {name}
                            </Link>
                          ) : (
                            <span className="text-slate-200 font-mono text-xs truncate max-w-[200px]">
                              {name}
                            </span>
                          )}
                          <span className="text-slate-500 text-xs ml-auto">{svc}</span>
                          <span
                            className={`text-xs ${running ? "text-emerald-400" : "text-slate-500"}`}
                          >
                            {status}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {logs && (
                <div className="bg-slate-900/60 border border-slate-800 rounded-lg">
                  <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-800 text-xs text-slate-500 font-medium">
                    <Terminal className="h-3.5 w-3.5" /> Logs (last 50 lines)
                  </div>
                  <pre className="text-xs text-slate-400 font-mono whitespace-pre-wrap max-h-48 overflow-y-auto p-3">
                    {logs}
                  </pre>
                </div>
              )}
            </>
          ) : (
            <div className="flex items-center justify-center h-48 text-sm text-slate-500">
              Select a compose project to inspect
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function FilesSortTh({
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
