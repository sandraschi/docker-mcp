import { AlertCircle, ArrowLeft, Loader2, Play } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ToolsHarnessExplainer } from "@/components/tools-harness-explainer";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { API_BASE } from "@/lib/api";
import {
  cleanArgs,
  emptyArgs,
  type JsonSchema,
  relatedPage,
  schemaType,
  type ToolMeta,
  toolCategory,
} from "@/lib/tool-schema";

function fieldValue(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "string") return value;
  if (typeof value === "boolean" || typeof value === "number") return String(value);
  return JSON.stringify(value);
}

export function ToolRunner() {
  const { name } = useParams();
  const toolName = name ? decodeURIComponent(name) : "";
  const [searchParams] = useSearchParams();
  const [tool, setTool] = useState<ToolMeta | null>(null);
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [confirm, setConfirm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<unknown>(null);

  const load = useCallback(async () => {
    if (!toolName) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/tools/${encodeURIComponent(toolName)}`);
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || `HTTP ${res.status}`);
      const meta = json.tool as ToolMeta;
      const initial = emptyArgs(meta.parameters);
      for (const [key, val] of searchParams.entries()) {
        if (key in initial || (meta.parameters?.properties && key in meta.parameters.properties)) {
          initial[key] = val;
        }
      }
      setTool(meta);
      setValues(initial);
      setError(null);
      setResult(null);
      setConfirm(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load tool");
      setTool(null);
    } finally {
      setLoading(false);
    }
  }, [toolName, searchParams]);

  useEffect(() => {
    load();
  }, [load]);

  const properties = useMemo(() => Object.entries(tool?.parameters?.properties || {}), [tool]);
  const required = useMemo(() => new Set(tool?.parameters?.required || []), [tool]);
  const related = tool ? relatedPage(tool.name) : null;

  const run = async () => {
    if (!tool) return;
    setRunning(true);
    setError(null);
    try {
      const arguments_ = cleanArgs(tool.parameters, values);
      const res = await fetch(`${API_BASE}/api/tools/${encodeURIComponent(tool.name)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ arguments: arguments_, confirm }),
      });
      const json = await res.json();
      if (!res.ok)
        throw new Error(typeof json.detail === "string" ? json.detail : `HTTP ${res.status}`);
      setResult(json.result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Invoke failed");
      setResult(null);
    } finally {
      setRunning(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[320px]">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (!tool) {
    return (
      <div className="space-y-4">
        <Link
          to="/tools"
          className="text-sm text-blue-400 hover:underline inline-flex items-center gap-1"
        >
          <ArrowLeft className="h-4 w-4" /> Tools
        </Link>
        <Card className="border-red-900/50 bg-red-950/20">
          <CardContent className="flex items-center gap-3 pt-6">
            <AlertCircle className="h-8 w-8 text-red-500 shrink-0" />
            <p className="text-red-200">{error ?? "Tool not found"}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <Link
            to="/tools"
            className="text-sm text-blue-400 hover:underline inline-flex items-center gap-1"
          >
            <ArrowLeft className="h-4 w-4" /> Tools
          </Link>
          <h2 className="text-2xl font-bold tracking-tight text-white mt-2 font-mono">
            {tool.name}
          </h2>
          <p className="text-slate-400 text-sm mt-1">{toolCategory(tool.name)}</p>
        </div>
        {related ? (
          <Link
            to={related}
            className="rounded-md bg-slate-800 px-3 py-2 text-sm text-slate-200 hover:bg-slate-700"
          >
            Related page
          </Link>
        ) : null}
      </div>

      <ToolsHarnessExplainer variant="compact" />

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader>
          <CardTitle className="text-white">Parameters</CardTitle>
          <CardDescription className="text-slate-400 whitespace-pre-wrap">
            {(tool.description || "No description").slice(0, 600)}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {properties.length === 0 ? (
            <p className="text-sm text-slate-500">No parameters. Run with empty arguments.</p>
          ) : (
            properties.map(([key, schema]) => (
              <Field
                key={key}
                name={key}
                schema={schema}
                required={required.has(key)}
                value={values[key]}
                onChange={(next) => setValues((prev) => ({ ...prev, [key]: next }))}
              />
            ))
          )}

          {tool.needs_confirm ? (
            <label className="flex items-center gap-2 text-sm text-amber-300">
              <input
                type="checkbox"
                checked={confirm}
                onChange={(e) => setConfirm(e.target.checked)}
              />
              I understand this can change Docker state
            </label>
          ) : null}

          <button
            type="button"
            onClick={() => void run()}
            disabled={running || (tool.needs_confirm && !confirm)}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
          >
            {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            {running ? "Running…" : "Run tool"}
          </button>
          {error ? <p className="text-sm text-red-400">{error}</p> : null}
        </CardContent>
      </Card>

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader>
          <CardTitle className="text-white">Result</CardTitle>
        </CardHeader>
        <CardContent>
          {result == null ? (
            <p className="text-sm text-slate-500">Not run yet</p>
          ) : (
            <pre className="text-xs font-mono text-slate-300 bg-slate-900/60 border border-slate-800 rounded-md p-4 max-h-[32rem] overflow-auto whitespace-pre-wrap">
              {typeof result === "string" ? result : JSON.stringify(result, null, 2)}
            </pre>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Field({
  name,
  schema,
  required,
  value,
  onChange,
}: {
  name: string;
  schema: JsonSchema;
  required: boolean;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  const kind = schemaType(schema);
  const label = `${name}${required ? " *" : ""}`;
  if (kind === "boolean") {
    return (
      <label className="flex items-center gap-2 text-sm text-slate-200">
        <input
          type="checkbox"
          checked={Boolean(value)}
          onChange={(e) => onChange(e.target.checked)}
        />
        <span>
          {label}
          {schema.description ? (
            <span className="block text-xs text-slate-500">{schema.description}</span>
          ) : null}
        </span>
      </label>
    );
  }

  if (schema.enum && schema.enum.length > 0) {
    return (
      <div className="grid gap-2">
        <Label className="text-slate-300">{label}</Label>
        {schema.description ? <p className="text-xs text-slate-500">{schema.description}</p> : null}
        <select
          value={fieldValue(value)}
          onChange={(e) => onChange(e.target.value)}
          className="h-10 rounded-md border border-slate-700 bg-slate-900 px-3 text-sm text-slate-200"
        >
          {!required ? <option value="">—</option> : null}
          {schema.enum.map((item) => (
            <option key={String(item)} value={String(item)}>
              {String(item)}
            </option>
          ))}
        </select>
      </div>
    );
  }

  if (kind === "object" || kind === "array") {
    return (
      <div className="grid gap-2">
        <Label className="text-slate-300">{label}</Label>
        {schema.description ? <p className="text-xs text-slate-500">{schema.description}</p> : null}
        <textarea
          value={fieldValue(value)}
          onChange={(e) => onChange(e.target.value)}
          rows={kind === "object" ? 4 : 3}
          placeholder={kind === "object" ? "{}" : "one, two  or JSON array"}
          className="rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm font-mono text-slate-200"
        />
      </div>
    );
  }

  return (
    <div className="grid gap-2">
      <Label className="text-slate-300">{label}</Label>
      {schema.description ? <p className="text-xs text-slate-500">{schema.description}</p> : null}
      <Input
        type={kind === "integer" || kind === "number" ? "number" : "text"}
        value={fieldValue(value)}
        onChange={(e) =>
          onChange(kind === "integer" || kind === "number" ? e.target.value : e.target.value)
        }
        className="bg-slate-900 border-slate-700 text-slate-100"
      />
    </div>
  );
}
