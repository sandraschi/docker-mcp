/** Image provenance + "what is this" helpers (mirrors backend image_provenance). */

export interface Provenance {
  ref: string;
  name: string;
  tag: string;
  registry: string | null;
  namespace: string | null;
  repo: string;
  kind: string;
  fleetRepo: string | null;
  hubUrl: string | null;
  githubUrl: string;
}

const FLEET_PREFIXES: Array<[string, string]> = [
  ["myai-", "myai"],
  ["deepfang-", "deepfang"],
  ["myconf-", "myconf"],
  ["tailscale-mcp-", "tailscale-mcp"],
];

const OFFICIAL = new Set([
  "postgres",
  "redis",
  "traefik",
  "nginx",
  "mongo",
  "mysql",
  "valkey",
  "python",
  "node",
  "alpine",
  "busybox",
]);

export const KIND_LABELS: Record<string, string> = {
  local: "Local build",
  "dockerhub-official": "Docker Hub official",
  "dockerhub-user": "Docker Hub",
  ghcr: "GHCR",
  lscr: "LinuxServer",
  gcr: "GCR",
  registry: "Registry",
};

export function splitRefTag(ref: string): [string, string] {
  const r = (ref || "").trim();
  if (r.includes("@")) {
    const [name, digest] = r.split("@");
    return [name, `@${digest}`];
  }
  const last = r.split("/").pop() ?? r;
  if (last.includes(":")) {
    const idx = r.lastIndexOf(":");
    return [r.slice(0, idx), r.slice(idx + 1)];
  }
  return [r, "latest"];
}

export function parseProvenance(ref: string): Provenance {
  const [name, tag] = splitRefTag(ref || "");
  const parts = name ? name.split("/") : [];
  let registry: string | null = null;
  let namespace: string | null = null;
  let repo = name;
  if (
    parts.length > 0 &&
    (parts[0].includes(".") || parts[0].includes(":") || parts[0] === "localhost")
  ) {
    registry = parts[0];
    const rest = parts.slice(1);
    if (rest.length > 1) {
      namespace = rest.slice(0, -1).join("/");
      repo = rest[rest.length - 1];
    } else if (rest.length === 1) {
      repo = rest[0];
    }
  } else if (parts.length > 1) {
    namespace = parts.slice(0, -1).join("/");
    repo = parts[parts.length - 1];
  } else if (parts.length === 1) {
    repo = parts[0];
  }

  let kind = "local";
  let fleetRepo: string | null = null;
  if (registry === "ghcr.io") kind = "ghcr";
  else if (registry === "lscr.io") kind = "lscr";
  else if (registry === "gcr.io" || registry === "k8s.gcr.io") kind = "gcr";
  else if (registry) kind = "registry";
  else if (namespace) kind = "dockerhub-user";
  else {
    for (const [prefix, frepo] of FLEET_PREFIXES) {
      if (repo.startsWith(prefix)) {
        fleetRepo = frepo;
        break;
      }
    }
    kind = fleetRepo || OFFICIAL.has(repo) ? (fleetRepo ? "local" : "dockerhub-official") : "local";
  }

  let hubUrl: string | null = null;
  if (kind === "dockerhub-official") hubUrl = `https://hub.docker.com/_/${repo}`;
  else if (kind === "dockerhub-user" && namespace)
    hubUrl = `https://hub.docker.com/r/${namespace}/${repo}`;
  else if (kind === "ghcr" && namespace) hubUrl = `https://github.com/${namespace}/${repo}`;

  const searchTerm = namespace && kind !== "ghcr" ? `${namespace}/${repo}` : repo;
  const githubUrl =
    kind === "ghcr" && hubUrl
      ? hubUrl
      : `https://github.com/search?q=${encodeURIComponent(searchTerm)}+in%3Aname&type=repositories`;

  return { ref, name, tag, registry, namespace, repo, kind, fleetRepo, hubUrl, githubUrl };
}

export function kindLabel(kind: string): string {
  return KIND_LABELS[kind] ?? kind;
}

/** Split a "repo:tag" or "repo@digest" ref into repository + tag parts for pull. */
export function splitRepoTag(ref: string): { repository: string; tag: string } {
  const [name, tag] = splitRefTag(ref);
  return { repository: name, tag: tag.startsWith("@") ? "latest" : tag };
}

/* What-is-this descriptions: known images first, heuristic fallback. */

const KNOWN: Array<[RegExp, string]> = [
  [/^postgres(:|$)/, "PostgreSQL relational database — data lives in its volume, port 5432."],
  [/^redis(:|$)|^valkey/i, "Redis-compatible in-memory store — cache / queues / sessions."],
  [/grafana\/grafana/, "Grafana dashboards — the web UI for metrics and logs (:3000)."],
  [/grafana\/loki/, "Loki log aggregation backend — stores logs, queried from Grafana."],
  [/grafana\/promtail/, "Promtail log shipper — tails container logs and forwards them to Loki."],
  [/grafana\/tempo/, "Tempo distributed tracing backend."],
  [/prom\/prometheus/, "Prometheus metrics database + alerting (:9090)."],
  [/prom\/node-exporter/, "Node exporter — exposes host CPU/mem/disk metrics to Prometheus."],
  [/prom\/blackbox-exporter/, "Blackbox exporter — probes HTTP/DNS/TCP endpoints for Prometheus."],
  [/cadvisor/, "cAdvisor — per-container CPU/memory stats for Prometheus."],
  [
    /opentelemetry-collector/,
    "OpenTelemetry collector — metrics/traces pipeline into Prometheus/Tempo.",
  ],
  [/^traefik/, "Traefik reverse proxy — routes host ports to containers."],
  [/goauthentik\/server/, "Authentik identity provider — SSO / login for self-hosted apps."],
  [/immich-server/, "Immich photo server — self-hosted Google Photos replacement."],
  [/immich-machine-learning/, "Immich ML worker — face recognition and visual search."],
  [/immich-app\/postgres/, "Immich-tuned Postgres (pgvector) — Immich metadata database."],
  [/open-webui/, "Open WebUI — chat frontend for local LLMs."],
  [/home-assistant/, "Home Assistant — smart-home hub (:8123)."],
  [/homarr/, "Homarr — self-hosted services dashboard."],
  [/andrius\/asterisk/, "Asterisk PBX — telephony / VoIP gateway."],
  [/rtorrent-rutorrent/, "rTorrent + ruTorrent seedbox (torrents)."],
  [/karust\/openserp/, "OpenSERP — self-hosted web-search API."],
  [/openssh-server/, "OpenSSH server container — remote shell access."],
  [/weaviate/, "Weaviate vector database — semantic search / RAG storage."],
  [/^myai-/, "Local build from the myai fleet repo (D:\\Dev\\repos\\myai)."],
  [/^deepfang-/, "Local build from the deepfang fleet repo (D:\\Dev\\repos\\deepfang)."],
  [/^myconf-/, "Local build from the myconf fleet repo (D:\\Dev\\repos\\myconf)."],
  [/^tailscale-mcp-/, "Local build from the tailscale-mcp fleet repo."],
];

export function describeImage(
  ref: string,
  detail?: { exposedPorts?: string[]; entrypoint?: unknown; cmd?: unknown },
): string {
  const short = ref.replace(/^sha256:/, "");
  for (const [re, text] of KNOWN) {
    if (re.test(short)) return text;
  }
  const bits: string[] = [];
  const ports = detail?.exposedPorts ?? [];
  if (ports.length > 0)
    bits.push(
      `exposes ${ports.slice(0, 4).join(", ")}${ports.length > 4 ? ` +${ports.length - 4}` : ""}`,
    );
  const entry = Array.isArray(detail?.entrypoint)
    ? (detail.entrypoint as string[]).join(" ")
    : (detail?.entrypoint as string) || "";
  const cmd = Array.isArray(detail?.cmd)
    ? (detail.cmd as string[]).join(" ")
    : (detail?.cmd as string) || "";
  const runs = [entry, cmd].filter(Boolean).join(" ").trim();
  if (runs) bits.push(`runs: ${runs.slice(0, 90)}${runs.length > 90 ? "…" : ""}`);
  if (bits.length === 0)
    return "No summary available — open the detail page for config, env and layer history.";
  return `Third-party image — ${bits.join("; ")}.`;
}
