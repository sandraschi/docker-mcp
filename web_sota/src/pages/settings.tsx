import { Cpu, FolderGit2, RefreshCw, Save, Server } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  getHealth,
  getLlmProviders,
  getLlmSettings,
  type LlmProvider,
  setLlmSettings,
} from "@/common/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { API_BASE } from "@/lib/api";

const DEFAULT_ENDPOINTS: Record<string, string> = {
  ollama: "http://127.0.0.1:11434",
  lmstudio: "http://127.0.0.1:1234",
};

export function Settings() {
  const [provider, setProvider] = useState(() => getLlmSettings().provider);
  const [model, setModel] = useState(() => getLlmSettings().model);
  const [endpoint, setEndpoint] = useState(() => getLlmSettings().endpoint);
  const [providers, setProviders] = useState<LlmProvider[]>([]);
  const [apiStatus, setApiStatus] = useState<string | null>(null);
  const [loadingModels, setLoadingModels] = useState(false);
  const [dockerStatus, setDockerStatus] = useState<Record<string, unknown> | null>(null);
  const [diagnostics, setDiagnostics] = useState<Record<string, unknown> | null>(null);
  const [engineError, setEngineError] = useState<string | null>(null);
  const [fleet, setFleet] = useState<{
    fleet_root?: string;
    exists?: boolean;
    is_default?: boolean;
    repo_count?: number;
    default?: string;
  } | null>(null);
  const [fleetInput, setFleetInput] = useState("");
  const [fleetMsg, setFleetMsg] = useState<string | null>(null);
  const [fleetSaving, setFleetSaving] = useState(false);

  const activeProvider = useMemo(
    () => providers.find((p) => p.type === provider),
    [providers, provider],
  );

  const modelOptions = useMemo(() => {
    const fromGlom = activeProvider?.models ?? [];
    if (fromGlom.length > 0) return fromGlom;
    return model ? [model] : [];
  }, [activeProvider, model]);

  const applyProvider = useCallback((next: string, list: LlmProvider[]) => {
    setProvider(next);
    const match = list.find((p) => p.type === next);
    if (match) {
      setEndpoint(match.base_url);
      if (match.models[0]) setModel(match.models[0]);
      return;
    }
    setEndpoint(DEFAULT_ENDPOINTS[next] ?? DEFAULT_ENDPOINTS.ollama);
  }, []);

  const refreshGlom = useCallback(
    async (force = false) => {
      setLoadingModels(true);
      setApiStatus("Querying Ollama and LM Studio…");
      try {
        const list = await getLlmProviders(force);
        setProviders(list);
        if (list.length === 0) {
          setApiStatus("No local LLM found (Ollama :11434, LM Studio :1234)");
          return;
        }
        const saved = getLlmSettings();
        const current = list.find((p) => p.type === (force ? provider : saved.provider)) ?? list[0];
        applyProvider(current.type, list);
        setApiStatus(
          `Discovered: ${list.map((p) => `${p.type} (${p.models.length} models)`).join(", ")}`,
        );
      } catch (err) {
        setApiStatus(err instanceof Error ? err.message : "Model discovery failed");
      } finally {
        setLoadingModels(false);
      }
    },
    [applyProvider, provider],
  );

  useEffect(() => {
    void (async () => {
      setLoadingModels(true);
      try {
        const list = await getLlmProviders(false);
        setProviders(list);
        if (list.length > 0) {
          const saved = getLlmSettings();
          const current = list.find((p) => p.type === saved.provider) ?? list[0];
          applyProvider(current.type, list);
          if (saved.model) setModel(saved.model);
        }
      } catch {
        /* non-fatal on mount */
      } finally {
        setLoadingModels(false);
      }
    })();
  }, [applyProvider]);

  useEffect(() => {
    void (async () => {
      try {
        const [statusRes, diagRes, fleetRes] = await Promise.all([
          fetch(`${API_BASE}/api/docker/status`),
          fetch(`${API_BASE}/api/v1/diagnostics`),
          fetch(`${API_BASE}/api/settings/fleet`),
        ]);
        if (statusRes.ok) setDockerStatus(await statusRes.json());
        if (diagRes.ok) setDiagnostics(await diagRes.json());
        if (fleetRes.ok) {
          const fleetJson = await fleetRes.json();
          setFleet(fleetJson);
          setFleetInput(String(fleetJson.fleet_root ?? ""));
        }
      } catch (e) {
        setEngineError(e instanceof Error ? e.message : "Failed to load engine status");
      }
    })();
  }, []);

  const saveFleetRoot = async (value: string) => {
    const next = value.trim();
    if (!next) {
      setFleetMsg("Enter a folder path first.");
      return;
    }
    setFleetSaving(true);
    setFleetMsg(null);
    try {
      const res = await fetch(`${API_BASE}/api/settings/fleet`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fleet_root: next }),
      });
      const json = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(json.detail || `HTTP ${res.status}`);
      setFleet(json);
      setFleetInput(String(json.fleet_root ?? next));
      setFleetMsg(
        json.warning ? String(json.warning) : `Saved — ${json.repo_count ?? 0} repos detected.`,
      );
    } catch (e) {
      setFleetMsg(e instanceof Error ? e.message : "Save failed");
    } finally {
      setFleetSaving(false);
    }
  };

  const onProviderChange = (next: string) => {
    applyProvider(next, providers);
  };

  const testApi = async () => {
    setApiStatus("Testing API…");
    try {
      await getHealth();
      setApiStatus("Backend reachable on port 10807");
    } catch (err) {
      setApiStatus(err instanceof Error ? err.message : "API test failed");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white">Settings</h2>
        <p className="text-slate-400">
          Local LLM glom-on (Ollama / LM Studio) and Docker MCP preferences
        </p>
      </div>

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Cpu className="h-5 w-5 text-blue-500" />
            <CardTitle className="text-white">Local LLM (Glom On)</CardTitle>
          </div>
          <CardDescription className="text-slate-400">
            Backend probes Ollama and LM Studio; models populate the dropdown below.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {providers.length > 0 ? (
            <ul className="space-y-1 text-sm text-emerald-300/90">
              {providers.map((p) => (
                <li key={p.type}>
                  {p.type} at {p.base_url}
                  {p.models.length > 0
                    ? ` — ${p.models.slice(0, 4).join(", ")}${p.models.length > 4 ? "…" : ""}`
                    : " — no models listed"}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">
              No providers discovered yet. Start Ollama or LM Studio, then refresh.
            </p>
          )}

          <div className="grid gap-4 md:grid-cols-3">
            <div className="grid gap-2">
              <Label className="text-slate-300">Provider</Label>
              <Select value={provider} onValueChange={onProviderChange}>
                <SelectTrigger className="bg-slate-900 border-slate-800 text-slate-100">
                  <SelectValue placeholder="Select provider" />
                </SelectTrigger>
                <SelectContent className="bg-slate-900 border-slate-800 text-slate-100">
                  <SelectItem value="ollama">Ollama</SelectItem>
                  <SelectItem value="lmstudio">LM Studio</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label className="text-slate-300">API endpoint</Label>
              <Input
                value={endpoint}
                onChange={(e) => setEndpoint(e.target.value)}
                className="bg-slate-900 border-slate-800 text-slate-100"
              />
            </div>
            <div className="grid gap-2">
              <Label className="text-slate-300">Model</Label>
              <Select
                value={model || undefined}
                onValueChange={setModel}
                disabled={modelOptions.length === 0}
              >
                <SelectTrigger className="bg-slate-900 border-slate-800 text-slate-100">
                  <SelectValue placeholder={loadingModels ? "Loading models…" : "Select a model"} />
                </SelectTrigger>
                <SelectContent className="bg-slate-900 border-slate-800 text-slate-100 max-h-64">
                  {modelOptions.map((m) => (
                    <SelectItem key={m} value={m}>
                      {m}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button
              className="bg-blue-600 hover:bg-blue-700 text-white"
              onClick={() => {
                setLlmSettings({ provider, model, endpoint });
                setApiStatus("LLM settings saved locally");
              }}
            >
              <Save className="mr-2 h-4 w-4" /> Save LLM settings
            </Button>
            <Button
              variant="outline"
              className="border-slate-800 text-slate-300 hover:bg-slate-800"
              disabled={loadingModels}
              onClick={() => void refreshGlom(true)}
            >
              <RefreshCw className={`mr-2 h-4 w-4 ${loadingModels ? "animate-spin" : ""}`} />
              Refresh models
            </Button>
            <Button
              variant="outline"
              className="border-slate-800 text-slate-300 hover:bg-slate-800"
              onClick={() => void testApi()}
            >
              Test API
            </Button>
          </div>
          {apiStatus && <p className="text-sm text-slate-400">{apiStatus}</p>}
        </CardContent>
      </Card>

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Server className="h-5 w-5 text-emerald-500" />
            <CardTitle className="text-white">Docker engine</CardTitle>
          </div>
          <CardDescription className="text-slate-400">
            Live status from GET /api/docker/status and GET /api/v1/diagnostics
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-slate-300 space-y-2">
          {engineError && <p className="text-red-400">{engineError}</p>}
          {dockerStatus ? (
            <ul className="space-y-1">
              <li>Daemon: {dockerStatus.docker_available ? "available" : "unavailable"}</li>
              <li>Version: {String(dockerStatus.version ?? "—")}</li>
              <li>API: {String(dockerStatus.api_version ?? "—")}</li>
              <li>OS: {String(dockerStatus.platform ?? "—")}</li>
              <li>
                Containers: {String(dockerStatus.containers_running ?? "—")} running /{" "}
                {String(dockerStatus.containers_total ?? "—")} total
              </li>
              <li>Images: {String(dockerStatus.images_count ?? "—")}</li>
              {dockerStatus.error ? (
                <li className="text-red-400">{String(dockerStatus.error)}</li>
              ) : null}
            </ul>
          ) : (
            <p className="text-slate-500">Loading Docker status…</p>
          )}
          {diagnostics ? (
            <p className="text-slate-400 pt-2">
              Tools: {String((diagnostics.tools as { total?: number } | undefined)?.total ?? "—")} ·
              Uptime:{" "}
              {Math.round(
                Number((diagnostics.backend as { uptime?: number } | undefined)?.uptime ?? 0),
              )}
              s
            </p>
          ) : null}
          <div className="flex flex-wrap gap-2 pt-3">
            <Link
              className="rounded-md bg-slate-800 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-700"
              to="/tools/docker_desktop_status"
            >
              Desktop status
            </Link>
            <Link
              className="rounded-md bg-slate-800 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-700"
              to="/tools/reconnect_docker"
            >
              Reconnect
            </Link>
            <Link
              className="rounded-md bg-slate-800 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-700"
              to="/tools/docker_daemon_restart"
            >
              Restart daemon
            </Link>
            <Link
              className="rounded-md bg-slate-800 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-700"
              to="/tools/docker_daemon_recover"
            >
              Recover
            </Link>
            <Link
              className="rounded-md bg-slate-800 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-700"
              to="/tools/list_gpus"
            >
              GPUs
            </Link>
            <Link
              className="rounded-md bg-slate-800 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-700"
              to="/tools/docker_backup"
            >
              Backup
            </Link>
          </div>
        </CardContent>
      </Card>

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader>
          <div className="flex items-center gap-2">
            <FolderGit2 className="h-5 w-5 text-violet-500" />
            <CardTitle className="text-white">Fleet repositories</CardTitle>
          </div>
          <CardDescription className="text-slate-400">
            Where your own repos live. Local images (myai-*, deepfang-*, …) are matched against this
            folder — anyone cloning from GitHub should point it at their checkout. The
            DOCKER_MCP_FLEET_ROOT env var overrides this file.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {fleet ? (
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="font-mono text-xs text-slate-200 break-all">{fleet.fleet_root}</span>
              {fleet.exists ? (
                <span className="inline-flex items-center rounded-full border border-emerald-800 bg-emerald-950/60 px-2 py-0.5 text-xs text-emerald-300">
                  {fleet.repo_count ?? 0} repos
                </span>
              ) : (
                <span className="inline-flex items-center rounded-full border border-amber-800 bg-amber-950/60 px-2 py-0.5 text-xs text-amber-300">
                  folder not found
                </span>
              )}
              {fleet.is_default ? (
                <span className="text-xs text-slate-500">default</span>
              ) : (
                <span className="text-xs text-slate-500">custom</span>
              )}
            </div>
          ) : (
            <p className="text-sm text-slate-500">Loading fleet location…</p>
          )}
          <div className="grid gap-2">
            <Label className="text-slate-300">Repos folder</Label>
            <Input
              value={fleetInput}
              onChange={(e) => setFleetInput(e.target.value)}
              placeholder="e.g. D:/Dev/repos or /home/you/fleet"
              className="bg-slate-900 border-slate-800 text-slate-100 font-mono text-sm"
            />
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              className="bg-blue-600 hover:bg-blue-700 text-white"
              disabled={fleetSaving}
              onClick={() => void saveFleetRoot(fleetInput)}
            >
              <Save className="mr-2 h-4 w-4" /> {fleetSaving ? "Saving…" : "Save folder"}
            </Button>
            <Button
              variant="outline"
              className="border-slate-800 text-slate-300 hover:bg-slate-800"
              disabled={fleetSaving || !fleet?.default}
              onClick={() => void saveFleetRoot(String(fleet?.default ?? ""))}
            >
              Reset to default
            </Button>
          </div>
          {fleetMsg && <p className="text-sm text-slate-400">{fleetMsg}</p>}
        </CardContent>
      </Card>

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader>
          <CardTitle className="text-white">App information</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-slate-400 space-y-1">
          <p>Docker MCP webapp (SOTA)</p>
          <p>Frontend: 10806 · Backend: 10807</p>
          <p>Event logs: /logs · Volumes: /volumes · Networks: /networks · Tools: /tools</p>
        </CardContent>
      </Card>
    </div>
  );
}
