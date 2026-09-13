import { AlertCircle, ArrowLeft, Loader2 } from "lucide-react";
import { type ReactNode, useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API_BASE } from "@/lib/api";
import { formatDate } from "@/lib/format";

interface VolumeDetailData {
  name: string;
  driver?: string;
  mountpoint?: string;
  created?: string;
  scope?: string;
  labels?: Record<string, string>;
  options?: Record<string, string>;
  usage_data?: { RefCount?: number; Size?: number };
}

export function VolumeDetail() {
  const { id } = useParams();
  const volumeName = id ? decodeURIComponent(id) : "";
  const [data, setData] = useState<VolumeDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!volumeName) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/volumes/${encodeURIComponent(volumeName)}`);
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || `HTTP ${res.status}`);
      setData(json.volume);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to inspect volume");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [volumeName]);

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
          to="/volumes"
          className="text-sm text-blue-400 hover:underline inline-flex items-center gap-1"
        >
          <ArrowLeft className="h-4 w-4" /> Back to volumes
        </Link>
        <Card className="border-red-900/50 bg-red-950/20">
          <CardContent className="flex items-center gap-3 pt-6">
            <AlertCircle className="h-8 w-8 text-red-500 shrink-0" />
            <p className="text-red-200">{error ?? "Volume not found"}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const labels = Object.entries(data.labels || {});
  const options = Object.entries(data.options || {});

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <Link
            to="/volumes"
            className="text-sm text-blue-400 hover:underline inline-flex items-center gap-1"
          >
            <ArrowLeft className="h-4 w-4" /> Volumes
          </Link>
          <h2 className="text-2xl font-bold tracking-tight text-white mt-2 break-all">
            {data.name}
          </h2>
          <p className="text-slate-400 text-xs mt-1">
            {data.driver || "local"} · {data.scope || "local"}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={load}
            className="rounded-md bg-slate-800 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700"
          >
            Refresh
          </button>
          <Link
            to={`/tools/remove_volume?name=${encodeURIComponent(data.name)}`}
            className="rounded-md bg-slate-800 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700"
          >
            Remove
          </Link>
          <Link
            to={`/tools/docker_backup?volume=${encodeURIComponent(data.name)}&operation=backup_volume`}
            className="rounded-md bg-slate-800 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700"
          >
            Backup
          </Link>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Meta label="Created" value={formatDate(data.created)} />
        <Meta
          label="Refs"
          value={data.usage_data?.RefCount == null ? "—" : String(data.usage_data.RefCount)}
        />
        <Meta
          label="Size"
          value={data.usage_data?.Size == null ? "—" : String(data.usage_data.Size)}
        />
      </div>

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader>
          <CardTitle className="text-white">Configuration</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm">
          <Row label="Mountpoint">
            <span className="font-mono text-xs break-all">{data.mountpoint || "—"}</span>
          </Row>
          <Row label="Driver">{data.driver || "—"}</Row>
          <Row label="Scope">{data.scope || "—"}</Row>
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
        <p className="text-lg font-semibold text-white">{value}</p>
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
