import { Bot, Boxes, Info, Layers, Wrench } from "lucide-react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Variant = "full" | "compact" | "dashboard";

export function ToolsHarnessExplainer({ variant = "full" }: { variant?: Variant }) {
  if (variant === "compact") {
    return (
      <p className="text-xs text-slate-500 border border-slate-800 rounded-md bg-slate-900/40 px-3 py-2">
        This form is the <strong className="text-slate-300">MCP tool harness</strong>: same tool and
        parameters Claude or Cursor use over MCP.{" "}
        <strong className="text-slate-300">Run tool</strong> calls{" "}
        <code className="text-blue-400">POST /api/tools/…</code> on the server, not a separate
        web-only API.
        <Link to="/tools#why-harness" className="text-blue-400 hover:underline ml-1">
          Why this UX?
        </Link>
      </p>
    );
  }

  if (variant === "dashboard") {
    return (
      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <Wrench className="h-4 w-4 text-blue-500" />
            <CardTitle className="text-sm font-medium text-slate-200">
              Why MCP Tools instead of more pages?
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="text-xs text-slate-400 space-y-2">
          <p>
            Docker MCP exposes <strong className="text-slate-300">40+ tools</strong> on one server.
            AI clients call them over MCP; this dashboard uses a{" "}
            <strong className="text-slate-300">single harness</strong> (catalog + schema forms) so
            every tool is runnable without building 40+ custom screens that would drift from the
            server.
          </p>
          <p>
            <Link to="/containers" className="text-blue-400 hover:underline">
              Containers
            </Link>
            ,{" "}
            <Link to="/images" className="text-blue-400 hover:underline">
              Images
            </Link>
            , and similar pages are for{" "}
            <strong className="text-slate-300">browsing and inspect</strong>. Backup, prune,
            diagnose, GPU, and daemon recovery live in the harness because they are MCP tools first.
          </p>
          <Link to="/tools#why-harness" className="text-blue-400 hover:underline inline-block">
            Read the full explanation on MCP Tools
          </Link>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card
      id="why-harness"
      className="border-blue-900/40 bg-gradient-to-br from-blue-950/20 via-slate-950/80 to-slate-950/50 scroll-mt-6"
    >
      <CardHeader>
        <div className="flex items-center gap-2">
          <Info className="h-5 w-5 text-blue-400" />
          <CardTitle className="text-white">What is this page? (the tool harness)</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="text-sm text-slate-300 space-y-4">
        <p>
          You are not looking at a random form builder. This is the{" "}
          <strong className="text-white">browser UI for the same MCP tools</strong> that Claude
          Desktop, Cursor, and other agents invoke on this server. Each card is one registered tool;{" "}
          <strong className="text-white">Run tool</strong> opens a form generated from that tool's
          JSON Schema, then executes it via{" "}
          <code className="text-blue-400 text-xs">POST /api/tools/{`{name}`}</code>.
        </p>

        <div className="grid gap-3 md:grid-cols-2">
          <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4 space-y-2">
            <div className="flex items-center gap-2 text-slate-200 font-medium">
              <Boxes className="h-4 w-4 text-emerald-400" />
              Browse pages (sidebar)
            </div>
            <p className="text-xs text-slate-400">
              Containers, Images, Volumes, Networks, Compose: tables, detail views, and a few REST
              actions (start/stop). Built for{" "}
              <strong className="text-slate-300">everyday navigation</strong> when you already know
              what you are looking at.
            </p>
          </div>
          <div className="rounded-lg border border-blue-900/50 bg-blue-950/20 p-4 space-y-2">
            <div className="flex items-center gap-2 text-slate-200 font-medium">
              <Wrench className="h-4 w-4 text-blue-400" />
              This harness (MCP Tools)
            </div>
            <p className="text-xs text-slate-400">
              Backup/restore, prune, agentic diagnose/cleanup, GPU containers, daemon recover, image
              compare, exec with custom args, prefab cards, and anything else exposed only as an MCP
              tool. One UI pattern covers <strong className="text-slate-300">all of them</strong>.
            </p>
          </div>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-4 space-y-2">
          <div className="flex items-center gap-2 text-slate-200 font-medium">
            <Bot className="h-4 w-4 text-purple-400" />
            Why not a dedicated page per activity?
          </div>
          <ul className="text-xs text-slate-400 space-y-1.5 list-disc ml-4">
            <li>
              <strong className="text-slate-300">Single source of truth</strong> — tool names,
              parameters, and behavior live in the FastMCP server. The harness introspects them; it
              does not re-implement Docker logic in React.
            </li>
            <li>
              <strong className="text-slate-300">No UI drift</strong> — when we add or change a
              tool, the catalog and forms update automatically. We do not maintain parallel
              &quot;web versions&quot; of 43 workflows.
            </li>
            <li>
              <strong className="text-slate-300">Parity with agents</strong> — what you run here is
              what an LLM would call; useful for debugging, ops, and learning what the server can
              do.
            </li>
            <li>
              <strong className="text-slate-300">Honest tradeoff</strong> — forms look generic
              because they are generic. Destructive tools require an explicit confirm checkbox. Use
              browse pages when a tailored table is enough; use the harness when you need the full
              tool surface.
            </li>
          </ul>
        </div>

        <p className="text-xs text-slate-500 flex items-center gap-1.5">
          <Layers className="h-3.5 w-3.5 shrink-0" />
          Cards with a <strong className="text-slate-400">Page</strong> button also have a related
          browse screen; the harness still runs the underlying MCP tool (often with more options
          than the page exposes).
        </p>
      </CardContent>
    </Card>
  );
}
