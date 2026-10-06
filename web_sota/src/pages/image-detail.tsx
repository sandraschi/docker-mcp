import { AlertCircle, ArrowLeft, Download, Loader2 } from "lucide-react";
import { type ReactNode, useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API_BASE } from "@/lib/api";
import { formatBytes, formatDate, shortId } from "@/lib/format";
import { describeImage, kindLabel, parseProvenance, splitRepoTag } from "@/lib/provenance";

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

interface ImageBrief {
  about?: string | null;
  github_repo?: string | null;
  github_url?: string;
  hub_url?: string | null;
  stars?: number | null;
  license?: string | null;
  topics?: string[];
  readme_excerpt?: string | null;
  error?: string | null;
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
  const [pullBusy, setPullBusy] = useState(false);
  const [pullMsg, setPullMsg] = useState<{ text: string; ok: boolean } | null>(null);
  const [brief, setBrief] = useState<ImageBrief | null>(null);

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

  // Upstream brief (Docker Hub / GitHub README lookup), loaded separately so a
  // slow or offline registry never blocks the config below.
  useEffect(() => {
    const tags = data?.tags?.length ? data.tags : null;
    const ref = tags ? tags[0] : imageRef;
    if (!ref || ref === "<none>") return;
    let cancelled = false;
    setBrief(null);
    const params = new URLSearchParams({ ref });
    fetch(`${API_BASE}/api/images/brief?${params.toString()}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((json) => {
        if (!cancelled && json) setBrief(json);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [data, imageRef]);

  const pull = async (ref: string) => {
    const { repository, tag } = splitRepoTag(ref);
    setPullBusy(true);
    setPullMsg(null);
    try {
      const res = await fetch(`${API_BASE}/api/images/pull`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repository, tag }),
      });
      const json = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(json.detail || `HTTP ${res.status}`);
      setPullMsg({ text: json.message || "done", ok: true });
      await load();
    } catch (e) {
      setPullMsg({ text: e instanceof Error ? e.message : "Pull failed", ok: false });
    } finally {
      setPullBusy(false);
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
  const primaryRef = tags[0] === "<none>" ? imageRef : tags[0];
  const prov = parseProvenance(primaryRef);
  const description = describeImage(primaryRef, {
    exposedPorts: data.exposed_ports,
    entrypoint: data.entrypoint,
    cmd: data.cmd,
  });

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
          {pullMsg && (
            <p className={`mt-2 text-sm ${pullMsg.ok ? "text-emerald-400" : "text-red-400"}`}>
              {pullMsg.text}
            </p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void pull(primaryRef)}
            disabled={pullBusy || primaryRef === "<none>"}
            title="Pull this tag — tells you if the local copy is already current"
            className="inline-flex items-center gap-1.5 rounded-md bg-blue-700 px-3 py-2 text-sm font-medium text-white hover:bg-blue-600 disabled:opacity-50"
          >
            {pullBusy ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
            {pullBusy ? "Pulling…" : "Pull"}
          </button>
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

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader>
          <CardTitle className="text-white">What is this?</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm leading-relaxed text-slate-200">{description}</p>
          {brief && (brief.about || brief.readme_excerpt) && (
            <div className="space-y-2 rounded-md border border-slate-800 bg-slate-900/60 p-3">
              <p className="text-[11px] uppercase tracking-wide text-slate-500">
                Upstream analysis{brief.github_repo ? ` — ${brief.github_repo}` : ""}
                {typeof brief.stars === "number" ? ` · ★ ${brief.stars.toLocaleString()}` : ""}
                {brief.license ? ` · ${brief.license}` : ""}
              </p>
              {brief.about && brief.about.slice(0, 60) !== description.slice(0, 60) && (
                <p className="text-[13px] leading-relaxed text-slate-300">{brief.about}</p>
              )}
              {(brief.topics || []).length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {(brief.topics || []).slice(0, 8).map((t) => (
                    <span
                      key={t}
                      className="rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 text-[11px] text-slate-400"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              )}
              {brief.readme_excerpt && (
                <div className="max-h-44 overflow-y-auto whitespace-pre-wrap text-xs leading-relaxed text-slate-400">
                  {brief.readme_excerpt}
                </div>
              )}
            </div>
          )}
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${
                prov.kind === "local"
                  ? "border-emerald-800 bg-emerald-950/60 text-emerald-300"
                  : prov.kind === "dockerhub-official"
                    ? "border-blue-800 bg-blue-950/60 text-blue-300"
                    : prov.kind === "ghcr"
                      ? "border-violet-800 bg-violet-950/60 text-violet-300"
                      : "border-slate-700 bg-slate-900 text-slate-300"
              }`}
            >
              {prov.fleetRepo ? `${prov.fleetRepo} (local build)` : kindLabel(prov.kind)}
            </span>
            {prov.fleetRepo && (
              <span className="font-mono text-xs text-slate-400">
                D:\Dev\repos\{prov.fleetRepo}
              </span>
            )}
          </div>
          <div className="grid gap-3 text-sm md:grid-cols-2">
            <Row label="Registry">{prov.registry || "(Docker Hub)"}</Row>
            <Row label="Repository">
              {[prov.namespace, prov.repo].filter(Boolean).join("/") || "—"}
            </Row>
            <Row label="Tag">{prov.tag}</Row>
            <Row label="Source links">
              <span className="flex flex-wrap gap-3">
                {prov.hubUrl && (
                  <a
                    href={prov.hubUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="text-blue-400 hover:underline"
                  >
                    {prov.kind === "ghcr" ? "GitHub repo" : "Docker Hub page"} ↗
                  </a>
                )}
                <a
                  href={prov.githubUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="text-blue-400 hover:underline"
                >
                  Find source on GitHub ↗
                </a>
              </span>
            </Row>
          </div>
          {tags.length > 1 && (
            <div>
              <p className="text-xs text-slate-500">Also tagged as</p>
              <p className="mt-0.5 break-all font-mono text-xs text-slate-300">
                {tags.slice(1).join(", ")}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

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
