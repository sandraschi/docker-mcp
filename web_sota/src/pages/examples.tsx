import {
  AlertCircle,
  CheckCircle2,
  FlaskConical,
  Loader2,
  Pencil,
  Play,
  Plus,
  RefreshCw,
  Trash2,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { API_BASE } from "@/lib/api";
import { type SortDir, useClientTable } from "@/lib/useClientTable";

interface ExampleInfo {
  name: string;
  title: string;
  description: string;
  lines: number;
  size: number;
}

interface RunResult {
  name: string;
  dry_run: boolean;
  exit_code: number;
  timed_out: boolean;
  duration_s: number;
  stdout: string;
  stderr: string;
  truncated: boolean;
}

interface SandboxContainer {
  id: string;
  name: string;
  image: string;
  state: string;
  created: string;
  restart_policy: string;
}

interface Mutation {
  status: string;
  dry_run: boolean;
  would?: string[];
  container?: SandboxContainer;
  removed?: string;
}

const DRY_RUN_KEY = "docker-mcp:examples:dry-run";
const SANDBOX_PAGE_SIZES = [10, 20, 50] as const;
const RESTART_POLICIES = ["no", "on-failure", "unless-stopped", "always"] as const;
const SANDBOX = "/api/examples/sandbox/containers";

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof data.detail === "string" ? data.detail : `HTTP ${res.status}`;
    throw Object.assign(new Error(detail), { status: res.status });
  }
  return data as T;
}

const errText = (e: unknown, fallback: string) => (e instanceof Error ? e.message : fallback);

// 503 from the sandbox endpoints means the Docker daemon is not reachable
const dockerErr = (e: unknown, fallback: string) =>
  (e as { status?: number }).status === 503
    ? `Docker is not reachable - start Docker Desktop, then press Refresh. (${errText(e, fallback)})`
    : errText(e, fallback);

function useDryRun(): [boolean, (value: boolean) => void] {
  const [dry, setDry] = useState(() => {
    try {
      return localStorage.getItem(DRY_RUN_KEY) !== "0";
    } catch {
      return true; // storage blocked: stay on the safe side
    }
  });
  const update = (value: boolean) => {
    setDry(value);
    try {
      localStorage.setItem(DRY_RUN_KEY, value ? "1" : "0");
    } catch {
      // storage blocked: the switch still works for this session
    }
  };
  return [dry, update];
}

function outcome(r: RunResult): { label: string; tone: "ok" | "warn" | "bad" } {
  if (r.timed_out) return { label: "Timed out", tone: "bad" };
  if (r.exit_code === 0) return { label: "Succeeded", tone: "ok" };
  if (r.exit_code === 2) return { label: "Docker not available", tone: "warn" };
  if (r.exit_code === 3) return { label: "Backend unreachable", tone: "bad" };
  return { label: `Failed (exit ${r.exit_code})`, tone: "bad" };
}

const TONE: Record<"ok" | "warn" | "bad", string> = {
  ok: "border-emerald-800 bg-emerald-950/60 text-emerald-300",
  warn: "border-amber-800 bg-amber-950/60 text-amber-300",
  bad: "border-red-800 bg-red-950/60 text-red-300",
};

function StateBadge({ state }: { state: string }) {
  const running = state === "running";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium ${
        running
          ? "border-emerald-800 bg-emerald-950/60 text-emerald-300"
          : "border-slate-700 bg-slate-800/60 text-slate-300"
      }`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${running ? "bg-emerald-400" : "bg-slate-500"}`} />
      {state || "—"}
    </span>
  );
}

function ErrorBanner({ message, testId }: { message: string; testId: string }) {
  return (
    <Card className="border-red-900/50 bg-red-950/20" data-testid={testId}>
      <CardContent className="flex items-center gap-3 pt-6">
        <AlertCircle className="h-6 w-6 shrink-0 text-red-500" />
        <p className="text-sm text-red-200">{message}</p>
      </CardContent>
    </Card>
  );
}

const btn =
  "inline-flex items-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium disabled:opacity-50";

// --- Run examples -----------------------------------------------------------------------------

function RunExamples({ dryRun }: { dryRun: boolean }) {
  const [examples, setExamples] = useState<ExampleInfo[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const [source, setSource] = useState<string>("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<RunResult | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  useEffect(() => {
    api<{ examples: ExampleInfo[] }>("/api/examples")
      .then((d) => {
        setExamples(d.examples);
        setSelected((cur) => cur ?? d.examples[0]?.name ?? null);
      })
      .catch((e) => setLoadError(errText(e, "Failed to load examples")))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selected) return;
    setSource("");
    setResult(null);
    setRunError(null);
    api<{ source: string }>(`/api/examples/${encodeURIComponent(selected)}/source`)
      .then((d) => setSource(d.source))
      .catch((e) => setSource(`# ${errText(e, "Failed to load source")}`));
  }, [selected]);

  const visible = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return examples;
    return examples.filter((e) =>
      `${e.name} ${e.title} ${e.description}`.toLowerCase().includes(q),
    );
  }, [examples, search]);

  const current = examples.find((e) => e.name === selected) ?? null;

  const run = async () => {
    if (!current) return;
    if (
      !dryRun &&
      !window.confirm(
        `Run ${current.name} for real? It may create and remove labelled resources on your Docker.`,
      )
    ) {
      return;
    }
    setRunning(true);
    setResult(null);
    setRunError(null);
    try {
      setResult(
        await api<RunResult>(`/api/examples/${encodeURIComponent(current.name)}/run`, {
          method: "POST",
          body: JSON.stringify({ dry_run: dryRun }),
        }),
      );
    } catch (e) {
      setRunError(errText(e, "Run failed"));
    } finally {
      setRunning(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[200px] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }
  if (loadError) return <ErrorBanner message={loadError} testId="examples-load-error" />;

  const verdict = result ? outcome(result) : null;

  return (
    <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader className="space-y-3">
          <CardTitle className="text-white">Scripts</CardTitle>
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter examples…"
            data-testid="examples-search"
            className="border-slate-700 bg-slate-900 text-slate-100"
          />
          <p className="text-xs text-slate-400" data-testid="examples-count">
            {visible.length} of {examples.length} examples
          </p>
        </CardHeader>
        <CardContent className="space-y-2">
          {visible.length === 0 && (
            <p className="text-sm text-slate-500">No example matches your filter.</p>
          )}
          {visible.map((ex) => (
            <button
              key={ex.name}
              type="button"
              data-testid={`example-${ex.name}`}
              onClick={() => setSelected(ex.name)}
              className={`w-full rounded-md border px-3 py-2 text-left ${
                ex.name === selected
                  ? "border-blue-600 bg-blue-950/40"
                  : "border-slate-800 bg-slate-900/60 hover:border-slate-600"
              }`}
            >
              <span className="block text-sm font-medium text-slate-100">{ex.title}</span>
              <span className="font-mono text-[11px] text-slate-400">
                {ex.name} · {ex.lines} lines
              </span>
            </button>
          ))}
        </CardContent>
      </Card>

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardTitle className="text-white">{current?.title ?? "Select an example"}</CardTitle>
            <button
              type="button"
              onClick={() => void run()}
              disabled={!current || running}
              data-testid="example-run"
              className={`${btn} ${dryRun ? "bg-blue-700 text-white hover:bg-blue-600" : "bg-red-800 text-red-50 hover:bg-red-700"}`}
            >
              {running ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              {running ? "Running…" : dryRun ? "Run (dry run)" : "Run for real"}
            </button>
          </div>
          {current?.description && (
            <p className="whitespace-pre-line text-sm text-slate-400">{current.description}</p>
          )}
        </CardHeader>
        <CardContent className="space-y-4">
          {runError && <ErrorBanner message={runError} testId="example-run-error" />}
          {result && verdict && (
            <div className="space-y-2" data-testid="example-result">
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span
                  data-testid="example-verdict"
                  className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${TONE[verdict.tone]}`}
                >
                  {verdict.tone === "ok" ? (
                    <CheckCircle2 className="h-3.5 w-3.5" />
                  ) : (
                    <XCircle className="h-3.5 w-3.5" />
                  )}
                  {verdict.label}
                </span>
                <span className="text-slate-400">
                  exit {result.exit_code} · {result.duration_s}s ·{" "}
                  {result.dry_run ? "dry run" : "real run"}
                </span>
                {result.truncated && <span className="text-amber-400">output truncated</span>}
              </div>
              <pre
                data-testid="example-output"
                className="max-h-80 overflow-auto rounded-md border border-slate-800 bg-black/40 p-3 font-mono text-xs text-slate-200"
              >
                {result.stdout || "(no output)"}
                {result.stderr && `\n--- stderr ---\n${result.stderr}`}
              </pre>
            </div>
          )}
          <div>
            <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">
              Source
            </p>
            <pre
              data-testid="example-source"
              className="max-h-96 overflow-auto rounded-md border border-slate-800 bg-slate-900/60 p-3 font-mono text-xs text-slate-300"
            >
              {source || "Loading…"}
            </pre>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// --- CRUD playground --------------------------------------------------------------------------

const randomName = () => `example-${Math.random().toString(36).slice(2, 6)}`;

const sortValue = (c: SandboxContainer, key: string): string | number => {
  switch (key) {
    case "image":
      return c.image;
    case "state":
      return c.state;
    case "restart":
      return c.restart_policy;
    case "created":
      return c.created;
    default:
      return c.name;
  }
};

function CrudPlayground({ dryRun }: { dryRun: boolean }) {
  const [rows, setRows] = useState<SandboxContainer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [plan, setPlan] = useState<{ title: string; steps: string[] } | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [name, setName] = useState(randomName);
  const [image, setImage] = useState("alpine:latest");
  const [command, setCommand] = useState("sleep 3600");

  const [editing, setEditing] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editPolicy, setEditPolicy] = useState("no");

  const [search, setSearch] = useState("");
  const [stateFilter, setStateFilter] = useState("all");
  const [sortKey, setSortKey] = useState("name");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState<number>(20);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const d = await api<{ containers: SandboxContainer[] }>(SANDBOX);
      setRows(d.containers);
      setError(null);
    } catch (e) {
      setRows([]);
      setError(dockerErr(e, "Failed to load example containers"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const afterMutation = async (title: string, m: Mutation) => {
    if (m.dry_run) {
      setPlan({ title, steps: m.would ?? [] });
      setNotice(null);
    } else {
      setPlan(null);
      setNotice(`${title}: done`);
      await load();
    }
  };

  const mutate = async (key: string, title: string, fn: () => Promise<Mutation>) => {
    setBusy(key);
    setError(null);
    setPlan(null);
    setNotice(null);
    try {
      await afterMutation(title, await fn());
    } catch (e) {
      setError(dockerErr(e, `${title} failed`));
    } finally {
      setBusy(null);
    }
  };

  const create = () =>
    mutate("create", "Create", () =>
      api<Mutation>(SANDBOX, {
        method: "POST",
        body: JSON.stringify({ name, image, command, dry_run: dryRun }),
      }).then((m) => {
        if (!m.dry_run) setName(randomName());
        return m;
      }),
    );

  const save = (id: string) =>
    mutate(`edit:${id}`, "Update", async () => {
      const m = await api<Mutation>(`${SANDBOX}/${encodeURIComponent(id)}`, {
        method: "PUT",
        body: JSON.stringify({ name: editName, restart_policy: editPolicy, dry_run: dryRun }),
      });
      if (!m.dry_run) setEditing(null);
      return m;
    });

  const remove = (c: SandboxContainer) => {
    if (!dryRun && !window.confirm(`Delete container ${c.name}? This cannot be undone.`)) return;
    void mutate(`delete:${c.id}`, "Delete", () =>
      api<Mutation>(`${SANDBOX}/${encodeURIComponent(c.id)}?dry_run=${dryRun}`, {
        method: "DELETE",
      }),
    );
  };

  const byState = useMemo(() => {
    if (stateFilter === "all") return rows;
    return rows.filter((c) =>
      stateFilter === "running" ? c.state === "running" : c.state !== "running",
    );
  }, [rows, stateFilter]);

  const match = useCallback(
    (c: SandboxContainer, q: string) =>
      `${c.name} ${c.image} ${c.state} ${c.restart_policy} ${c.id}`.toLowerCase().includes(q),
    [],
  );

  const table = useClientTable(byState, {
    search,
    match,
    sortKey,
    sortDir,
    sortValue,
    page,
    pageSize,
  });

  const toggleSort = (key: string) => {
    setPage(0);
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortKey(key);
      setSortDir("asc");
    }
  };
  const arrow = (key: string) => (sortKey === key ? (sortDir === "asc" ? " ▲" : " ▼") : "");
  const th =
    "cursor-pointer select-none px-3 py-2 text-left text-xs font-medium uppercase tracking-wide text-slate-400";
  const field = "h-10 rounded-md border border-slate-700 bg-slate-900 px-3 text-sm text-slate-200";

  return (
    <div className="space-y-4">
      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader>
          <CardTitle className="text-white">Create an example container</CardTitle>
          <p className="text-sm text-slate-400">
            Every container here is labelled{" "}
            <code className="text-slate-200">docker-mcp.example=1</code>. Update and delete refuse
            anything without that label, so your real containers are never touched.
          </p>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-3">
          <div className="space-y-1">
            <label htmlFor="crud-name" className="text-xs text-slate-400">
              Name
            </label>
            <Input
              id="crud-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              data-testid="crud-name"
              className="w-48 border-slate-700 bg-slate-900 text-slate-100"
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="crud-image" className="text-xs text-slate-400">
              Image
            </label>
            <Input
              id="crud-image"
              value={image}
              onChange={(e) => setImage(e.target.value)}
              data-testid="crud-image"
              className="w-48 border-slate-700 bg-slate-900 text-slate-100"
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="crud-command" className="text-xs text-slate-400">
              Command
            </label>
            <Input
              id="crud-command"
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              data-testid="crud-command"
              className="w-48 border-slate-700 bg-slate-900 text-slate-100"
            />
          </div>
          <button
            type="button"
            onClick={() => void create()}
            disabled={busy !== null}
            data-testid="crud-create"
            className={`${btn} bg-blue-700 text-white hover:bg-blue-600`}
          >
            {busy === "create" ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Plus className="h-4 w-4" />
            )}
            {dryRun ? "Create (dry run)" : "Create"}
          </button>
        </CardContent>
      </Card>

      {error && <ErrorBanner message={error} testId="crud-error" />}
      {notice && (
        <p className="text-sm text-emerald-400" data-testid="crud-notice">
          {notice}
        </p>
      )}
      {plan && (
        <Card className="border-blue-900/60 bg-blue-950/20" data-testid="crud-plan">
          <CardContent className="space-y-1 pt-6 text-sm">
            <p className="font-medium text-blue-200">Dry run - {plan.title} would:</p>
            <ul className="list-inside list-disc text-slate-300">
              {plan.steps.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
            <p className="text-xs text-slate-500">
              Nothing was sent to Docker. Switch Dry run off to do it for real.
            </p>
          </CardContent>
        </Card>
      )}

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardTitle className="text-white">Example containers</CardTitle>
            <button
              type="button"
              onClick={() => void load()}
              disabled={loading}
              data-testid="crud-refresh"
              className={`${btn} bg-slate-800 text-slate-200 hover:bg-slate-700`}
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </button>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Input
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(0);
              }}
              placeholder="Filter name, image, state…"
              data-testid="crud-search"
              className="max-w-xs border-slate-700 bg-slate-900 text-slate-100"
            />
            <select
              value={stateFilter}
              onChange={(e) => {
                setStateFilter(e.target.value);
                setPage(0);
              }}
              data-testid="crud-state-filter"
              className={field}
            >
              <option value="all">All states</option>
              <option value="running">Running</option>
              <option value="stopped">Not running</option>
            </select>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setPage(0);
              }}
              data-testid="crud-page-size"
              className={field}
            >
              {SANDBOX_PAGE_SIZES.map((n) => (
                <option key={n} value={n}>
                  {n} / page
                </option>
              ))}
            </select>
            <span className="text-sm text-slate-400" data-testid="crud-count">
              {table.filteredCount} of {rows.length} containers
            </span>
          </div>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          {loading && rows.length === 0 ? (
            <Loader2 className="mx-auto h-6 w-6 animate-spin text-blue-500" />
          ) : rows.length === 0 && !error ? (
            <p className="py-6 text-center text-sm text-slate-500" data-testid="crud-empty">
              No example containers yet. Create one above.
            </p>
          ) : (
            <table className="w-full text-sm" data-testid="crud-table">
              <thead>
                <tr className="border-b border-slate-800">
                  <th className={th} onClick={() => toggleSort("name")}>
                    Name{arrow("name")}
                  </th>
                  <th className={th} onClick={() => toggleSort("image")}>
                    Image{arrow("image")}
                  </th>
                  <th className={th} onClick={() => toggleSort("state")}>
                    State{arrow("state")}
                  </th>
                  <th className={th} onClick={() => toggleSort("restart")}>
                    Restart policy{arrow("restart")}
                  </th>
                  <th className={th} onClick={() => toggleSort("created")}>
                    Created{arrow("created")}
                  </th>
                  <th className={th}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {table.rows.map((c) => (
                  <tr
                    key={c.id}
                    className="border-b border-slate-900"
                    data-testid={`crud-row-${c.name}`}
                  >
                    {editing === c.id ? (
                      <>
                        <td className="px-3 py-2">
                          <Input
                            value={editName}
                            onChange={(e) => setEditName(e.target.value)}
                            data-testid="crud-edit-name"
                            className="h-8 w-40 border-slate-700 bg-slate-900 text-slate-100"
                          />
                        </td>
                        <td className="px-3 py-2 font-mono text-xs text-slate-300">{c.image}</td>
                        <td className="px-3 py-2">
                          <StateBadge state={c.state} />
                        </td>
                        <td className="px-3 py-2">
                          <select
                            value={editPolicy}
                            onChange={(e) => setEditPolicy(e.target.value)}
                            data-testid="crud-edit-policy"
                            className={`${field} h-8`}
                          >
                            {RESTART_POLICIES.map((p) => (
                              <option key={p} value={p}>
                                {p}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td className="px-3 py-2 text-xs text-slate-400">
                          {c.created.slice(0, 19).replace("T", " ")}
                        </td>
                        <td className="px-3 py-2">
                          <span className="inline-flex gap-1">
                            <button
                              type="button"
                              onClick={() => void save(c.id)}
                              disabled={busy !== null}
                              data-testid="crud-save"
                              className="rounded-md bg-emerald-800 px-2 py-1 text-xs text-emerald-50 hover:bg-emerald-700 disabled:opacity-50"
                            >
                              {dryRun ? "Save (dry run)" : "Save"}
                            </button>
                            <button
                              type="button"
                              onClick={() => setEditing(null)}
                              className="rounded-md bg-slate-800 px-2 py-1 text-xs text-slate-200 hover:bg-slate-700"
                            >
                              Cancel
                            </button>
                          </span>
                        </td>
                      </>
                    ) : (
                      <>
                        <td className="px-3 py-2 font-medium text-slate-100">{c.name}</td>
                        <td className="px-3 py-2 font-mono text-xs text-slate-300">{c.image}</td>
                        <td className="px-3 py-2">
                          <StateBadge state={c.state} />
                        </td>
                        <td className="px-3 py-2 text-slate-300">{c.restart_policy}</td>
                        <td className="px-3 py-2 text-xs text-slate-400">
                          {c.created.slice(0, 19).replace("T", " ")}
                        </td>
                        <td className="px-3 py-2">
                          <span className="inline-flex gap-1">
                            <button
                              type="button"
                              onClick={() => {
                                setEditing(c.id);
                                setEditName(c.name);
                                setEditPolicy(c.restart_policy);
                              }}
                              disabled={busy !== null}
                              data-testid={`crud-edit-${c.name}`}
                              className="inline-flex items-center gap-1 rounded-md bg-slate-800 px-2 py-1 text-xs text-slate-200 hover:bg-slate-700 disabled:opacity-50"
                            >
                              <Pencil className="h-3 w-3" /> Edit
                            </button>
                            <button
                              type="button"
                              onClick={() => remove(c)}
                              disabled={busy !== null}
                              data-testid={`crud-delete-${c.name}`}
                              className="inline-flex items-center gap-1 rounded-md bg-red-900 px-2 py-1 text-xs text-red-100 hover:bg-red-800 disabled:opacity-50"
                            >
                              <Trash2 className="h-3 w-3" />{" "}
                              {dryRun ? "Delete (dry run)" : "Delete"}
                            </button>
                          </span>
                        </td>
                      </>
                    )}
                  </tr>
                ))}
                {table.rows.length === 0 && rows.length > 0 && (
                  <tr>
                    <td colSpan={6} className="py-6 text-center text-sm text-slate-500">
                      No container matches your filter.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
          {rows.length > 0 && (
            <div
              className="mt-3 flex items-center justify-between text-sm text-slate-400"
              data-testid="crud-pager"
            >
              <button
                type="button"
                disabled={table.page === 0}
                onClick={() => setPage(table.page - 1)}
                className="rounded-md bg-slate-800 px-3 py-1 disabled:opacity-40"
              >
                Prev
              </button>
              <span>
                Page {table.page + 1} of {table.pageCount}
              </span>
              <button
                type="button"
                disabled={table.page >= table.pageCount - 1}
                onClick={() => setPage(table.page + 1)}
                className="rounded-md bg-slate-800 px-3 py-1 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// --- Page ----------------------------------------------------------------------------------------

export function Examples() {
  const [dryRun, setDryRun] = useDryRun();

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="flex items-center gap-2 text-2xl font-bold tracking-tight text-white">
            <FlaskConical className="h-6 w-6 text-blue-500" />
            Examples
          </h2>
          <p className="max-w-2xl text-slate-400">
            Run the scripts from the repo's <code className="text-slate-200">examples/</code> folder
            and try a small create / read / update / delete playground on labelled example
            containers.
          </p>
        </div>
        <div
          className={`flex items-center gap-3 rounded-md border px-4 py-2 ${dryRun ? "border-blue-800 bg-blue-950/30" : "border-red-800 bg-red-950/30"}`}
        >
          <Switch
            id="dry-run"
            checked={dryRun}
            onCheckedChange={setDryRun}
            data-testid="dry-run-switch"
          />
          <label htmlFor="dry-run" className="cursor-pointer text-sm">
            <span className="block font-medium text-slate-100">
              Dry run {dryRun ? "on" : "off"}
            </span>
            <span className="block text-xs text-slate-400">
              {dryRun ? "Nothing touches Docker" : "Changes are applied for real"}
            </span>
          </label>
        </div>
      </div>

      <Tabs defaultValue="run">
        <TabsList>
          <TabsTrigger value="run" data-testid="tab-run">
            Run examples
          </TabsTrigger>
          <TabsTrigger value="crud" data-testid="tab-crud">
            CRUD playground
          </TabsTrigger>
        </TabsList>
        <TabsContent value="run" className="mt-4">
          <RunExamples dryRun={dryRun} />
        </TabsContent>
        <TabsContent value="crud" className="mt-4">
          <CrudPlayground dryRun={dryRun} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
