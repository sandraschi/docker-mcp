import { AlertCircle, ArrowLeft, Loader2 } from "lucide-react";
import { type ReactNode, useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API_BASE } from "@/lib/api";
import { formatDate, resourceHref, shortId } from "@/lib/format";

interface ContainerDetailData {
  id: string;
  name: string;
  image: string;
  image_id?: string;
  status: string;
  state?: Record<string, unknown>;
  created?: string;
  command?: string[] | string | null;
  entrypoint?: string[] | string | null;
  working_dir?: string;
  user?: string;
  hostname?: string;
  environment?: Record<string, string>;
  labels?: Record<string, string>;
  ports?: string[];
  networks?: Record<
    string,
    { ip_address?: string; gateway?: string; mac_address?: string; aliases?: string[] }
  >;
  mounts?: Array<Record<string, unknown>>;
  restart_policy?: Record<string, unknown>;
  privileged?: boolean;
  compose_project?: string | null;
  compose_service?: string | null;
}

function asText(value: unknown): string {
  if (value == null || value === "") return "—";
  if (Array.isArray(value)) return value.join(" ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export function ContainerDetail() {
  const { id } = useParams();
  const containerId = id ? decodeURIComponent(id) : "";
  const [data, setData] = useState<ContainerDetailData | null>(null);
  const [logs, setLogs] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!containerId) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/containers/${encodeURIComponent(containerId)}`);
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || `HTTP ${res.status}`);
      setData(json.container);
      setError(null);
      const logRes = await fetch(
        `${API_BASE}/api/containers/${encodeURIComponent(containerId)}/logs?tail=200`,
      );
      if (logRes.ok) {
        const logJson = await logRes.json();
        setLogs(logJson.logs || "");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to inspect container");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [containerId]);

  useEffect(() => {
    load();
  }, [load]);

  const runAction = async (action: "start" | "stop" | "restart") => {
    if (!containerId) return;
    setActionBusy(action);
    setActionError(null);
    try {
      const res = await fetch(
        `${API_BASE}/api/containers/${encodeURIComponent(containerId)}/${action}`,
        { method: "POST" },
      );
      const json = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = typeof json.detail === "string" ? json.detail : `HTTP ${res.status}`;
        throw new Error(detail);
      }
      await load();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : `${action} failed`);
    } finally {
      setActionBusy(null);
    }
  };

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center min-h-[320px]">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-4">
        <Link
          to="/containers"
          className="text-sm text-blue-400 hover:underline inline-flex items-center gap-1"
        >
          <ArrowLeft className="h-4 w-4" /> Back to containers
        </Link>
        <Card className="border-red-900/50 bg-red-950/20">
          <CardContent className="flex items-center gap-3 pt-6">
            <AlertCircle className="h-8 w-8 text-red-500 shrink-0" />
            <p className="text-red-200">{error ?? "Container not found"}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const state = (data.state?.Status as string) || data.status;
  const exitCode = data.state?.ExitCode;
  const imageHref = data.image ? resourceHref("images", data.image) : null;
  const envEntries = Object.entries(data.environment || {});
  const labelEntries = Object.entries(data.labels || {});
  const mounts = data.mounts || [];
  const networks = Object.entries(data.networks || {});

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <Link
            to="/containers"
            className="text-sm text-blue-400 hover:underline inline-flex items-center gap-1"
          >
            <ArrowLeft className="h-4 w-4" /> Containers
          </Link>
          <h2 className="text-2xl font-bold tracking-tight text-white mt-2">{data.name}</h2>
          <p className="text-slate-400 font-mono text-xs mt-1">{data.id}</p>
          {actionError ? <p className="text-sm text-red-400 mt-2">{actionError}</p> : null}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {state !== "running" && (
            <button
              type="button"
              disabled={Boolean(actionBusy)}
              onClick={() => void runAction("start")}
              className="rounded-md bg-emerald-700 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-600 disabled:opacity-50"
            >
              {actionBusy === "start" ? "Starting…" : "Start"}
            </button>
          )}
          {state === "running" && (
            <>
              <button
                type="button"
                disabled={Boolean(actionBusy)}
                onClick={() => void runAction("stop")}
                className="rounded-md bg-red-800 px-3 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
              >
                {actionBusy === "stop" ? "Stopping…" : "Stop"}
              </button>
              <button
                type="button"
                disabled={Boolean(actionBusy)}
                onClick={() => void runAction("restart")}
                className="rounded-md bg-amber-700 px-3 py-2 text-sm font-medium text-white hover:bg-amber-600 disabled:opacity-50"
              >
                {actionBusy === "restart" ? "Restarting…" : "Restart"}
              </button>
            </>
          )}
          <button
            type="button"
            onClick={load}
            className="rounded-md bg-slate-800 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700"
          >
            Refresh
          </button>
          <Link
            to={`/tools/container_analyze?container_id=${encodeURIComponent(containerId)}`}
            className="rounded-md bg-slate-800 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700"
          >
            Analyze
          </Link>
          <Link
            to={`/tools/execute_in_container?container_id=${encodeURIComponent(containerId)}`}
            className="rounded-md bg-slate-800 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700"
          >
            Exec
          </Link>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Meta label="State" value={state} tone={state === "running" ? "ok" : "muted"} />
        <Meta label="Created" value={formatDate(data.created)} />
        <Meta label="Restart" value={asText((data.restart_policy || {}).Name)} />
        <Meta label="Exit code" value={exitCode == null ? "—" : String(exitCode)} />
      </div>

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader>
          <CardTitle className="text-white">Configuration</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm md:grid-cols-2">
          <Row label="Image">
            {imageHref ? (
              <Link to={imageHref} className="text-blue-400 hover:underline font-mono text-xs">
                {data.image}
              </Link>
            ) : (
              <span className="font-mono text-xs">{data.image || "—"}</span>
            )}
          </Row>
          <Row label="Image ID">
            <span className="font-mono text-xs">{shortId(data.image_id, 19)}</span>
          </Row>
          <Row label="Command">{asText(data.command)}</Row>
          <Row label="Entrypoint">{asText(data.entrypoint)}</Row>
          <Row label="Working dir">{data.working_dir || "—"}</Row>
          <Row label="User">{data.user || "—"}</Row>
          <Row label="Hostname">{data.hostname || "—"}</Row>
          <Row label="Privileged">{data.privileged ? "yes" : "no"}</Row>
          <Row label="Compose">
            {data.compose_project ? (
              <Link to="/compose" className="text-blue-400 hover:underline">
                {data.compose_project}
                {data.compose_service ? ` / ${data.compose_service}` : ""}
              </Link>
            ) : (
              "—"
            )}
          </Row>
          <Row label="Ports">{data.ports?.length ? data.ports.join(", ") : "—"}</Row>
        </CardContent>
      </Card>

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader>
          <CardTitle className="text-white">Networks</CardTitle>
        </CardHeader>
        <CardContent>
          {networks.length === 0 ? (
            <p className="text-slate-500 text-sm">No networks</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-400 border-b border-slate-800">
                  <th className="pb-2 pr-4">Name</th>
                  <th className="pb-2 pr-4">IP</th>
                  <th className="pb-2 pr-4">Gateway</th>
                  <th className="pb-2">MAC</th>
                </tr>
              </thead>
              <tbody>
                {networks.map(([name, net]) => (
                  <tr key={name} className="border-b border-slate-800/80">
                    <td className="py-2 pr-4">
                      <Link
                        to={resourceHref("networks", name)}
                        className="text-blue-400 hover:underline"
                      >
                        {name}
                      </Link>
                    </td>
                    <td className="py-2 pr-4 font-mono text-xs">{net.ip_address || "—"}</td>
                    <td className="py-2 pr-4 font-mono text-xs">{net.gateway || "—"}</td>
                    <td className="py-2 font-mono text-xs">{net.mac_address || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader>
          <CardTitle className="text-white">Mounts ({mounts.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {mounts.length === 0 ? (
            <p className="text-slate-500 text-sm">No mounts</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-slate-400 border-b border-slate-800">
                    <th className="pb-2 pr-4">Type</th>
                    <th className="pb-2 pr-4">Source</th>
                    <th className="pb-2 pr-4">Destination</th>
                    <th className="pb-2">Mode</th>
                  </tr>
                </thead>
                <tbody>
                  {mounts.map((mount, i) => (
                    <tr key={i} className="border-b border-slate-800/80">
                      <td className="py-2 pr-4">{asText(mount.Type)}</td>
                      <td className="py-2 pr-4 font-mono text-xs break-all">
                        {String(mount.Type) === "volume" && (mount.Name || mount.Source) ? (
                          <Link
                            to={resourceHref("volumes", String(mount.Name || mount.Source))}
                            className="text-blue-400 hover:underline"
                          >
                            {asText(mount.Source || mount.Name)}
                          </Link>
                        ) : (
                          asText(mount.Source)
                        )}
                      </td>
                      <td className="py-2 pr-4 font-mono text-xs">{asText(mount.Destination)}</td>
                      <td className="py-2">{asText(mount.Mode || mount.RW)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="border-slate-800 bg-slate-950/50">
          <CardHeader>
            <CardTitle className="text-white">Environment ({envEntries.length})</CardTitle>
          </CardHeader>
          <CardContent className="max-h-80 overflow-y-auto space-y-1 font-mono text-xs">
            {envEntries.length === 0 ? (
              <p className="text-slate-500">None</p>
            ) : (
              envEntries.map(([k, v]) => (
                <p key={k} className="text-slate-300 break-all">
                  <span className="text-slate-500">{k}=</span>
                  {v}
                </p>
              ))
            )}
          </CardContent>
        </Card>
        <Card className="border-slate-800 bg-slate-950/50">
          <CardHeader>
            <CardTitle className="text-white">Labels ({labelEntries.length})</CardTitle>
          </CardHeader>
          <CardContent className="max-h-80 overflow-y-auto space-y-1 font-mono text-xs">
            {labelEntries.length === 0 ? (
              <p className="text-slate-500">None</p>
            ) : (
              labelEntries.map(([k, v]) => (
                <p key={k} className="text-slate-300 break-all">
                  <span className="text-slate-500">{k}=</span>
                  {v}
                </p>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader>
          <CardTitle className="text-white">Logs (last 200)</CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="text-xs font-mono text-slate-300 bg-slate-900/60 border border-slate-800 rounded-md p-4 max-h-96 overflow-auto whitespace-pre-wrap">
            {logs.trim() || "No logs"}
          </pre>
        </CardContent>
      </Card>
    </div>
  );
}

function Meta({ label, value, tone }: { label: string; value: string; tone?: "ok" | "muted" }) {
  return (
    <Card className="border-slate-800 bg-slate-950/50">
      <CardContent className="pt-4">
        <p className="text-xs text-slate-400">{label}</p>
        <p className={`text-lg font-semibold ${tone === "ok" ? "text-emerald-400" : "text-white"}`}>
          {value}
        </p>
      </CardContent>
    </Card>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <p className="text-xs text-slate-500">{label}</p>
      <div className="text-slate-200 mt-0.5">{children}</div>
    </div>
  );
}
