import { AlertCircle, Loader2, Wrench } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ToolsHarnessExplainer } from "@/components/tools-harness-explainer";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { API_BASE } from "@/lib/api";
import { CATEGORY_ORDER, relatedPage, type ToolMeta, toolCategory } from "@/lib/tool-schema";

function normalizeTools(raw: unknown): ToolMeta[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((item) => {
    if (typeof item === "string") return { name: item, description: "" };
    return item as ToolMeta;
  });
}

export function Tools() {
  const [tools, setTools] = useState<ToolMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    const fetchTools = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/tools`);
        const data = await response.json();
        setTools(normalizeTools(data.tools));
      } catch (error) {
        console.error("Failed to fetch tools", error);
      } finally {
        setLoading(false);
      }
    };
    fetchTools();
  }, []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return tools;
    return tools.filter((tool) => {
      const hay = `${tool.name} ${tool.description || ""} ${toolCategory(tool.name)}`.toLowerCase();
      return hay.includes(q);
    });
  }, [tools, search]);

  const groups = useMemo(() => {
    const map = new Map<string, ToolMeta[]>();
    for (const tool of filtered) {
      const cat = toolCategory(tool.name);
      const list = map.get(cat) || [];
      list.push(tool);
      map.set(cat, list);
    }
    return CATEGORY_ORDER.filter((cat) => map.has(cat)).map(
      (cat) => [cat, map.get(cat) || []] as const,
    );
  }, [filtered]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">MCP tool harness</h2>
          <p className="text-slate-400 max-w-2xl">
            {loading ? "Loading…" : `${filtered.length} of ${tools.length} tools`} from the server —
            same surface AI clients use. Pick a card, fill the generated form, click Run.
          </p>
        </div>
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Filter tools…"
          className="max-w-sm bg-slate-900 border-slate-700 text-slate-100"
        />
      </div>

      <ToolsHarnessExplainer variant="full" />

      {loading ? (
        <div className="flex items-center justify-center p-12">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        </div>
      ) : (
        groups.map(([category, items]) => (
          <div key={category} className="space-y-3">
            <h3 className="text-sm font-medium uppercase tracking-wider text-slate-500">
              {category}
            </h3>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {items.map((tool) => {
                const href = `/tools/${encodeURIComponent(tool.name)}`;
                const related = relatedPage(tool.name);
                return (
                  <Card
                    key={tool.name}
                    className="border-slate-800 bg-slate-950/50 hover:bg-slate-900/50 transition-colors"
                  >
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between gap-2">
                        <CardTitle className="text-sm font-semibold text-white font-mono break-all">
                          {tool.name}
                        </CardTitle>
                        <Wrench className="h-4 w-4 text-blue-500 shrink-0" />
                      </div>
                      <CardDescription className="text-xs text-slate-400 min-h-[2.5rem]">
                        {(tool.description || "MCP tool").slice(0, 160)}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="flex gap-2">
                      <Link
                        to={href}
                        className="inline-flex flex-1 items-center justify-center rounded-md bg-blue-600 px-3 py-2 text-sm text-white hover:bg-blue-500"
                      >
                        Run tool
                      </Link>
                      {related ? (
                        <Link
                          to={related}
                          className="inline-flex items-center justify-center rounded-md bg-slate-800 px-3 py-2 text-sm text-slate-200 hover:bg-slate-700"
                        >
                          Page
                        </Link>
                      ) : null}
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </div>
        ))
      )}

      {!loading && filtered.length === 0 && (
        <div className="flex flex-col items-center justify-center p-12 border border-dashed border-slate-800 rounded-lg">
          <AlertCircle className="h-8 w-8 text-slate-600 mb-2" />
          <p className="text-slate-500">No tools match</p>
        </div>
      )}
    </div>
  );
}
