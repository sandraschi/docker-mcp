export interface JsonSchema {
  type?: string | string[];
  properties?: Record<string, JsonSchema>;
  required?: string[];
  default?: unknown;
  description?: string;
  enum?: unknown[];
  items?: JsonSchema;
  additionalProperties?: boolean | JsonSchema;
}

export interface ToolMeta {
  name: string;
  title?: string | null;
  description?: string;
  parameters?: JsonSchema;
  annotations?: Record<string, unknown> | null;
  tags?: string[];
  needs_confirm?: boolean;
}

export function schemaType(schema: JsonSchema | undefined): string {
  const raw = schema?.type;
  if (Array.isArray(raw)) return raw.find((item) => item !== "null") || "string";
  return raw || (schema?.enum ? "string" : schema?.properties ? "object" : "string");
}

export function emptyArgs(schema: JsonSchema | undefined): Record<string, unknown> {
  const props = schema?.properties || {};
  const values: Record<string, unknown> = {};
  for (const [key, prop] of Object.entries(props)) {
    if (prop.default !== undefined) {
      values[key] = prop.default;
      continue;
    }
    const kind = schemaType(prop);
    if (kind === "boolean") values[key] = false;
    else if (kind === "number" || kind === "integer") values[key] = "";
    else if (kind === "array") values[key] = "";
    else if (kind === "object") values[key] = "{}";
    else values[key] = "";
  }
  return values;
}

export function cleanArgs(
  schema: JsonSchema | undefined,
  raw: Record<string, unknown>,
): Record<string, unknown> {
  const props = schema?.properties || {};
  const required = new Set(schema?.required || []);
  const out: Record<string, unknown> = {};
  for (const [key, prop] of Object.entries(props)) {
    const kind = schemaType(prop);
    const value = raw[key];
    if (kind === "boolean") {
      out[key] = Boolean(value);
      continue;
    }
    if (value === "" || value == null) {
      if (required.has(key)) out[key] = kind === "array" ? [] : kind === "object" ? {} : value;
      continue;
    }
    if (kind === "integer") {
      const n = Number(value);
      if (!Number.isNaN(n)) out[key] = Math.trunc(n);
      continue;
    }
    if (kind === "number") {
      const n = Number(value);
      if (!Number.isNaN(n)) out[key] = n;
      continue;
    }
    if (kind === "array") {
      if (Array.isArray(value)) {
        out[key] = value;
      } else if (typeof value === "string") {
        const trimmed = value.trim();
        if (trimmed.startsWith("[")) {
          try {
            out[key] = JSON.parse(trimmed);
          } catch {
            out[key] = trimmed
              .split(",")
              .map((item) => item.trim())
              .filter(Boolean);
          }
        } else {
          out[key] = trimmed
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean);
        }
      }
      continue;
    }
    if (kind === "object") {
      if (typeof value === "object") {
        out[key] = value;
      } else if (typeof value === "string") {
        try {
          out[key] = JSON.parse(value);
        } catch {
          out[key] = value;
        }
      }
      continue;
    }
    out[key] = value;
  }
  return out;
}

export function toolCategory(name: string): string {
  const n = name.toLowerCase();
  if (n.includes("gpu")) return "GPU";
  if (n.includes("volume")) return "Volumes";
  if (n.includes("network")) return "Networks";
  if (n.includes("image") || n === "tag_image" || n === "search_images") return "Images";
  if (n.includes("backup")) return "Backup";
  if (n.includes("agentic") || n.includes("workflow")) return "Workflows";
  if (
    n.includes("desktop") ||
    n.includes("daemon") ||
    n.includes("reconnect") ||
    n.includes("status_tool")
  ) {
    return "Daemon";
  }
  if (n.includes("card")) return "Cards";
  if (n.includes("container") || n.includes("exec") || n === "get_container_logs")
    return "Containers";
  if (n.includes("system") || n.includes("disk") || n.includes("prune") || n.includes("duration"))
    return "System";
  return "Other";
}

export function relatedPage(name: string): string | null {
  const n = name.toLowerCase();
  if (n.includes("volume")) return "/volumes";
  if (n.includes("network")) return "/networks";
  if (n.includes("image") || n === "tag_image" || n === "search_images") return "/images";
  if (n.includes("compose")) return "/compose";
  if (n.includes("container") || n.includes("exec") || n === "get_container_logs")
    return "/containers";
  if (n.includes("log")) return "/logs";
  if (n.includes("desktop") || n.includes("daemon") || n.includes("status")) return "/settings";
  if (n.includes("system") || n.includes("disk")) return "/";
  return null;
}

export const CATEGORY_ORDER = [
  "Containers",
  "Images",
  "Volumes",
  "Networks",
  "GPU",
  "System",
  "Daemon",
  "Backup",
  "Workflows",
  "Cards",
  "Other",
];
