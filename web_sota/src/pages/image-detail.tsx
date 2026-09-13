import { AlertCircle, ArrowLeft, Loader2 } from "lucide-react";
import { type ReactNode, useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API_BASE } from "@/lib/api";
import { formatBytes, formatDate, shortId } from "@/lib/format";

interface ImageDetailData {
  id: string;
  tags?: string[];
  repo_digests?: string[];
  created?: string;
  size?: number;
  architecture?: string;
  os?: string;
  variant?: string;
  author?: string;
  comment?: string;
  docker_version?: string;
  parent?: string;
  labels?: Record<string, string>;
  env?: string[];
  cmd?: string[] | string | null;
  entrypoint?: string[] | string | null;
  working_dir?: string;
  user?: string;
  exposed_ports?: string[];
  volumes?: string[];
  rootfs?: { Type?: string; Layers?: string[] };
}

interface HistoryItem {
  id?: string;
  created?: string;
  created_by?: string;
  size?: number;
  tags?: string[];
}

function asText(value: unknown): string {
  if (value == null || value === "") return "—";
  if (Array.isArray(value)) return value.join(" ");
  return String(value);
}

export function ImageDetail() {
  const { id } = useParams();
  const imageRef = id ? decodeURIComponent(id) : "";
  const [data, setData] = useState<ImageDetailData | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!imageRef) return;
    setLoading(true);
    try {
      const params = new URLSearchParams({ ref: imageRef });
      const res = await fetch(`${API_BASE}/api/images/inspect?${params.toString()}`);
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || `HTTP ${res.status}`);
      setData(json.image);
      setError(null);
      const histRes = await fetch(`${API_BASE}/api/images/history?${params.toString()}`);
      if (histRes.ok) {
        const histJson = await histRes.json();
        setHistory(histJson.history || []);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to inspect image");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [imageRef]);

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
          to="/images"
          className="text-sm text-blue-400 hover:underline inline-flex items-center gap-1"
        >
          <ArrowLeft className="h-4 w-4" /> Back to images
        </Link>
        <Card className="border-red-900/50 bg-red-950/20">
          <CardContent className="flex items-center gap-3 pt-6">
            <AlertCircle className="h-8 w-8 text-red-500 shrink-0" />
            <p className="text-red-200">{error ?? "Image not found"}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const tags = data.tags?.length ? data.tags : ["<none>"];
  const labels = Object.entries(data.labels || {});

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <Link
            to="/images"
            className="text-sm text-blue-400 hover:underline inline-flex items-center gap-1"
          >
            <ArrowLeft className="h-4 w-4" /> Images
          </Link>
          <h2 className="text-2xl font-bold tracking-tight text-white mt-2 break-all">{tags[0]}</h2>
          <p className="text-slate-400 font-mono text-xs mt-1">{data.id}</p>
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
            to={`/tools/tag_image?image_id=${encodeURIComponent(tags[0] || imageRef)}`}
            className="rounded-md bg-slate-800 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700"
          >
            Tag
          </Link>
          <Link
            to={`/tools/image_compare?image_a=${encodeURIComponent(tags[0] || imageRef)}`}
            className="rounded-md bg-slate-800 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700"
          >
            Compare
          </Link>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Meta label="Size" value={formatBytes(data.size)} />
        <Meta label="Created" value={formatDate(data.created)} />
        <Meta label="OS / Arch" value={`${data.os || "—"} / ${data.architecture || "—"}`} />
        <Meta label="Layers" value={String(data.rootfs?.Layers?.length ?? history.length)} />
      </div>

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader>
          <CardTitle className="text-white">Configuration</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm md:grid-cols-2">
          <Row label="Tags">{tags.join(", ")}</Row>
          <Row label="Digests">
            {data.repo_digests?.length ? data.repo_digests.join(", ") : "—"}
          </Row>
          <Row label="Entrypoint">{asText(data.entrypoint)}</Row>
          <Row label="Cmd">{asText(data.cmd)}</Row>
          <Row label="Working dir">{data.working_dir || "—"}</Row>
          <Row label="User">{data.user || "—"}</Row>
          <Row label="Exposed ports">
            {data.exposed_ports?.length ? data.exposed_ports.join(", ") : "—"}
          </Row>
          <Row label="Volumes">{data.volumes?.length ? data.volumes.join(", ") : "—"}</Row>
          <Row label="Author">{data.author || "—"}</Row>
          <Row label="Docker">{data.docker_version || "—"}</Row>
          <Row label="Parent">{data.parent ? shortId(data.parent, 19) : "—"}</Row>
          <Row label="Comment">{data.comment || "—"}</Row>
        </CardContent>
      </Card>

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader>
          <CardTitle className="text-white">Environment</CardTitle>
        </CardHeader>
        <CardContent className="max-h-64 overflow-y-auto space-y-1 font-mono text-xs">
          {(data.env || []).length === 0 ? (
            <p className="text-slate-500">None</p>
          ) : (
            (data.env || []).map((line) => (
              <p key={line} className="text-slate-300 break-all">
                {line}
              </p>
            ))
          )}
        </CardContent>
      </Card>

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader>
          <CardTitle className="text-white">Labels ({labels.length})</CardTitle>
        </CardHeader>
        <CardContent className="max-h-64 overflow-y-auto space-y-1 font-mono text-xs">
          {labels.length === 0 ? (
            <p className="text-slate-500">None</p>
          ) : (
            labels.map(([k, v]) => (
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
          <CardTitle className="text-white">History ({history.length})</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          {history.length === 0 ? (
            <p className="text-slate-500 text-sm">No layer history</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-400 border-b border-slate-800">
                  <th className="pb-2 pr-4">Created</th>
                  <th className="pb-2 pr-4">Size</th>
                  <th className="pb-2">Created by</th>
                </tr>
              </thead>
              <tbody>
                {history.map((layer, i) => (
                  <tr key={`${layer.id}-${i}`} className="border-b border-slate-800/80 align-top">
                    <td className="py-2 pr-4 whitespace-nowrap text-slate-400">
                      {formatDate(layer.created)}
                    </td>
                    <td className="py-2 pr-4 whitespace-nowrap">{formatBytes(layer.size)}</td>
                    <td className="py-2 font-mono text-xs text-slate-300 break-all">
                      {layer.created_by || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
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

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <p className="text-xs text-slate-500">{label}</p>
      <div className="text-slate-200 mt-0.5 break-all">{children}</div>
    </div>
  );
}
