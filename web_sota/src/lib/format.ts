export function formatBytes(bytes: number | undefined | null): string {
  if (bytes == null || Number.isNaN(bytes)) return "—";
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.min(sizes.length - 1, Math.floor(Math.log(bytes) / Math.log(k)));
  return `${Number.parseFloat((bytes / k ** i).toFixed(1))} ${sizes[i]}`;
}

export function formatDate(value: string | undefined | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export function shortId(id: string | undefined | null, len = 12): string {
  if (!id) return "—";
  const bare = id.replace(/^sha256:/, "");
  return bare.length > len ? bare.slice(0, len) : bare;
}

export function resourceHref(
  kind: "containers" | "images" | "volumes" | "networks",
  id: string,
): string {
  return `/${kind}/${encodeURIComponent(id)}`;
}

export function imageRef(img: { id?: string; repo_tags?: string[] }): string {
  const tag = img.repo_tags?.find((t) => t && t !== "<none>:<none>");
  return tag || img.id || "";
}

export function formatAge(value: string | undefined | null, now = Date.now()): string {
  if (!value) return "—";
  const date = new Date(value);
  const time = date.getTime();
  if (Number.isNaN(time)) return value;
  const diffMs = now - time;
  if (diffMs < 0) return "in the future";
  const seconds = Math.floor(diffMs / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}mo ago`;
  const years = Math.floor(months / 12);
  return `${years}y ago`;
}

export function truncate(value: string | undefined | null, maxLen = 60): string {
  if (!value) return "—";
  if (value.length <= maxLen) return value;
  return `${value.slice(0, maxLen - 1)}…`;
}
