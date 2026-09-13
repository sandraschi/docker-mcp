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
