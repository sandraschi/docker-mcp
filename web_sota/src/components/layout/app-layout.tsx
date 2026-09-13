import { useEffect, useState } from "react";
import { useZoom } from "@/lib/useZoom";
import { useConnection } from "@/store/connection";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";

// import { Toaster } from '@/components/ui/toaster';

const BACKEND_PORT = 10807;
const HEALTH_OK_MS = 15000;
const DOCKER_STATUS_MS = 30000;
const BACKOFF_MS = [2000, 4000, 8000, 16000, 30000];

interface AppLayoutProps {
  children: React.ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  useZoom();
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;
    let attempt = 0;
    let lastDockerAt = 0;

    const poll = async () => {
      if (cancelled) return;
      try {
        const r = await fetch(`http://127.0.0.1:${BACKEND_PORT}/api/health`, {
          signal: AbortSignal.timeout(5000),
        });
        if (cancelled) return;
        if (r.ok) {
          useConnection.setState({ state: "connected" });
          attempt = 0;
          const now = Date.now();
          if (now - lastDockerAt >= DOCKER_STATUS_MS) {
            lastDockerAt = now;
            try {
              const ds = await fetch(`http://127.0.0.1:${BACKEND_PORT}/api/docker/status`, {
                signal: AbortSignal.timeout(5000),
              });
              if (cancelled) return;
              if (ds.ok) {
                const body = await ds.json();
                useConnection.setState({
                  dockerAvailable: Boolean(body.docker_available),
                  dockerVersion: body.version ?? null,
                  lastError: body.error ?? null,
                });
              }
            } catch {
              if (!cancelled) useConnection.setState({ dockerAvailable: null });
            }
          }
        } else {
          useConnection.setState({ state: "offline", lastError: `HTTP ${r.status}` });
          attempt = Math.min(attempt + 1, BACKOFF_MS.length - 1);
        }
      } catch (e) {
        if (cancelled) return;
        useConnection.setState({
          state: "offline",
          lastError: e instanceof Error ? e.message : "Network error",
        });
        attempt = Math.min(attempt + 1, BACKOFF_MS.length - 1);
      }
      if (cancelled) return;
      const delay = attempt === 0 ? HEALTH_OK_MS : BACKOFF_MS[attempt];
      timer = window.setTimeout(poll, delay);
    };

    poll();
    return () => {
      cancelled = true;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, []);

  // Tauri event bridge
  useEffect(() => {
    let unlisten: (() => void) | undefined;
    (async () => {
      try {
        const { listen } = await import("@tauri-apps/api/event");
        unlisten = await listen<string>("backend-status", (event) => {
          if (event.payload === "ready") useConnection.setState({ state: "connected" });
          else if (event.payload?.startsWith("error:"))
            useConnection.setState({ state: "error", lastError: event.payload });
        });
      } catch {
        // Not inside Tauri — HTTP polling handles it
      }
    })();
    return () => {
      if (unlisten) unlisten();
    };
  }, []);

  // Persist sidebar state
  useEffect(() => {
    const stored = localStorage.getItem("sidebar-collapsed");
    if (stored !== null) setCollapsed(stored === "true");
  }, []);

  const handleToggle = () => {
    const newState = !collapsed;
    setCollapsed(newState);
    localStorage.setItem("sidebar-collapsed", String(newState));
  };

  return (
    <div className="flex min-h-screen flex-col bg-slate-950 text-slate-50 font-sans selection:bg-emerald-500/30">
      <div className="flex flex-1 overflow-hidden">
        <Sidebar collapsed={collapsed} onToggle={handleToggle} />
        <div className="flex flex-1 flex-col overflow-hidden">
          <Topbar />
          <main className="flex-1 overflow-y-auto p-6 scroll-smooth">
            <div className="mx-auto max-w-7xl animate-in fade-in duration-500">{children}</div>
          </main>
        </div>
      </div>
      {/* <Toaster /> */}
    </div>
  );
}
