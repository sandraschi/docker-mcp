import { AlertCircle, ArrowLeft, Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API_BASE } from "@/lib/api";
import { formatDate, resourceHref, shortId } from "@/lib/format";

interface AttachedContainer {
  id: string;
  name: string;
  ipv4?: string;
  ipv6?: string;
  mac?: string;
}

interface NetworkDetailData {
  id: string;
  name: string;
  driver?: string;
  scope?: string;
  created?: string;
  internal?: boolean;
  attachable?: boolean;
  ingress?: boolean;
  enable_ipv6?: boolean;
  ipam?: Record<string, unknown>;
  options?: Record<string, string>;
  labels?: Record<string, string>;
  containers?: AttachedContainer[];
}

export function NetworkDetail() {
  const { id } = useParams();
  const networkId = id ? decodeURIComponent(id) : "";
  const [data, setData] = useState<NetworkDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!networkId) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/networks/${encodeURIComponent(networkId)}`);
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || `HTTP ${res.status}`);
      setData(json.network);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to inspect network");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [networkId]);

  useEffect(() => {
    load();
  }, [load]);

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
          to="/networks"
          className="text-sm text-blue-400 hover:underline inline-flex items-center gap-1"
        >
          <ArrowLeft className="h-4 w-4" /> Back to networks
        </Link>
        <Card className="border-red-900/50 bg-red-950/20">
          <CardContent className="flex items-center gap-3 pt-6">
            <AlertCircle className="h-8 w-8 text-red-500 shrink-0" />
            <p className="text-red-200">{error ?? "Network not found"}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const attached = data.containers || [];
  const labels = Object.entries(data.labels || {});
  const options = Object.entries(data.options || {});
  const ipam = data.ipam || {};
  const configs = Array.isArray(ipam.Config) ? ipam.Config : [];

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <Link
            to="/networks"
            className="text-sm text-blue-400 hover:underline inline-flex items-center gap-1"
          >
            <ArrowLeft className="h-4 w-4" /> Networks
          </Link>
          <h2 className="text-2xl font-bold tracking-tight text-white mt-2">{data.name}</h2>
          <p className="text-slate-400 font-mono text-xs mt-1">{data.id}</p>
        </div>
        <button
          type="button"
          onClick={load}
          className="rounded-md bg-slate-800 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700"
        >
          Refresh
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Meta label="Driver" value={data.driver || "—"} />
        <Meta label="Scope" value={data.scope || "—"} />
        <Meta label="Created" value={formatDate(data.created)} />
        <Meta
          label="Flags"
          value={
            [
              data.internal && "internal",
              data.attachable && "attachable",
              data.ingress && "ingress",
              data.enable_ipv6 && "ipv6",
            ]
              .filter(Boolean)
              .join(", ") || "—"
          }
        />
      </div>

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader>
          <CardTitle className="text-white">IPAM</CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-2">
          <p className="text-slate-400">Driver: {String(ipam.Driver || "—")}</p>
          {configs.length === 0 ? (
            <p className="text-slate-500">No subnet config</p>
          ) : (
            configs.map((cfg, i) => {
              const row = cfg as Record<string, string>;
              return (
                <p key={i} className="font-mono text-xs text-slate-300">
                  {row.Subnet || "?"} {row.Gateway ? `gw ${row.Gateway}` : ""}
                </p>
              );
            })
          )}
        </CardContent>
      </Card>

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader>
          <CardTitle className="text-white">Attached containers ({attached.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {attached.length === 0 ? (
            <p className="text-slate-500 text-sm">No containers</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-400 border-b border-slate-800">
                  <th className="pb-2 pr-4">Name</th>
                  <th className="pb-2 pr-4">ID</th>
                  <th className="pb-2 pr-4">IPv4</th>
                  <th className="pb-2">MAC</th>
                </tr>
              </thead>
              <tbody>
                {attached.map((c) => (
                  <tr key={c.id} className="border-b border-slate-800/80">
                    <td className="py-2 pr-4">
                      <Link
                        to={resourceHref("containers", c.id)}
                        className="text-blue-400 hover:underline"
                      >
                        {c.name || shortId(c.id)}
                      </Link>
                    </td>
                    <td className="py-2 pr-4 font-mono text-xs text-slate-400">{shortId(c.id)}</td>
                    <td className="py-2 pr-4 font-mono text-xs">{c.ipv4 || "—"}</td>
                    <td className="py-2 font-mono text-xs">{c.mac || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <KvCard title={`Labels (${labels.length})`} entries={labels} />
        <KvCard title={`Options (${options.length})`} entries={options} />
      </div>
    </div>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <Card className="border-slate-800 bg-slate-950/50">
      <CardContent className="pt-4">
        <p className="text-xs text-slate-400">{label}</p>
        <p className="text-lg font-semibold text-white break-all">{value}</p>
      </CardContent>
    </Card>
  );
}

function KvCard({ title, entries }: { title: string; entries: [string, string][] }) {
  return (
    <Card className="border-slate-800 bg-slate-950/50">
      <CardHeader>
        <CardTitle className="text-white">{title}</CardTitle>
      </CardHeader>
      <CardContent className="max-h-80 overflow-y-auto space-y-1 font-mono text-xs">
        {entries.length === 0 ? (
          <p className="text-slate-500">None</p>
        ) : (
          entries.map(([k, v]) => (
            <p key={k} className="text-slate-300 break-all">
              <span className="text-slate-500">{k}=</span>
              {v}
            </p>
          ))
        )}
      </CardContent>
    </Card>
  );
}
