import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { HelpCircle, Book, Shield, Zap, Info, AlertCircle, Wrench, Server, Cpu, GitBranch, MessageSquare } from "lucide-react";

const TABS = [
  { id: "about", label: "About", icon: Info },
  { id: "architecture", label: "Architecture", icon: GitBranch },
  { id: "usage", label: "Usage", icon: Book },
  { id: "docker", label: "Docker", icon: Server },
];

export function Help() {
    const [activeTab, setActiveTab] = useState("about");

    const tabBar = (
        <div className="flex gap-1 border-b border-slate-800 pb-0.5">
            {TABS.map((t) => (
                <button
                    key={t.id}
                    type="button"
                    onClick={() => setActiveTab(t.id)}
                    className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors ${
                        activeTab === t.id
                            ? "bg-slate-800/60 text-white border border-b-0 border-slate-700"
                            : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/30"
                    }`}
                >
                    <t.icon className="h-4 w-4" />
                    {t.label}
                </button>
            ))}
        </div>
    );

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-2xl font-bold tracking-tight text-white">Help & Documentation</h2>
                <p className="text-slate-400">Reference guide for Docker MCP Server with Desktop Management</p>
            </div>

            {tabBar}

            {activeTab === "about" && (
                <div className="grid gap-6 md:grid-cols-2">
                    <Card className="border-slate-800 bg-slate-950/50 md:col-span-2">
                        <CardHeader>
                            <div className="flex items-center gap-2">
                                <Info className="h-5 w-5 text-emerald-500" />
                                <CardTitle className="text-white">About Docker MCP</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent className="text-sm text-slate-400 space-y-3">
                            <p><strong>Docker MCP</strong> is an AI-powered Docker management server. It exposes Docker operations as MCP tools consumable by LLM agents (Claude Desktop, Cursor) and provides a React dashboard for manual management.</p>
                            <p>Part of the <strong>Sandra SOTA Fleet</strong>. Designed for Windows with Docker Desktop, supports container lifecycle, image management, volume/network operations, daemon health monitoring, and automatic hang recovery via the triple-kill pattern.</p>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3">
                                {[
                                    { label: "Version", value: "3.3.0", icon: Info },
                                    { label: "Backend", value: "127.0.0.1:10807", icon: Server },
                                    { label: "Frontend", value: "127.0.0.1:10806", icon: Zap },
                                    { label: "MCP endpoint", value: "/mcp (HTTP SSE)", icon: MessageSquare },
                                ].map((s) => (
                                    <div key={s.label} className="bg-slate-900/60 rounded-lg p-3 border border-slate-800">
                                        <div className="flex items-center gap-2 text-xs text-slate-500 mb-1">
                                            <s.icon className="h-3 w-3" />
                                            {s.label}
                                        </div>
                                        <div className="text-sm font-mono text-slate-200">{s.value}</div>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="border-slate-800 bg-slate-950/50">
                        <CardHeader>
                            <div className="flex items-center gap-2">
                                <Shield className="h-5 w-5 text-purple-500" />
                                <CardTitle className="text-white">Security & Auth</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent className="text-sm text-slate-400 space-y-2">
                            <p>Web access requires Basic Authentication. Default: <code className="text-blue-400">sandra / sandra123</code>.</p>
                            <p>Docker socket accessed locally only (named pipes on Windows).</p>
                            <p>Resource limits recommended for AI workloads: 12GB+ memory, 4+ CPUs.</p>
                        </CardContent>
                    </Card>

                    <Card className="border-slate-800 bg-slate-950/50">
                        <CardHeader>
                            <div className="flex items-center gap-2">
                                <Zap className="h-5 w-5 text-yellow-500" />
                                <CardTitle className="text-white">Tech Stack</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent className="text-sm text-slate-400 space-y-1">
                            <p>FastMCP 3.2+ · FastAPI · React 19 · Vite · TailwindCSS</p>
                            <p>Python 3.12+ · Docker SDK for Python · PyInstaller</p>
                            <p>Tauri 2.0 desktop wrapper · NSIS installer</p>
                            <p className="text-xs text-slate-500 mt-2">Fleet standards: mcp-central-docs/standards/</p>
                        </CardContent>
                    </Card>
                </div>
            )}

            {activeTab === "architecture" && (
                <div className="grid gap-6 md:grid-cols-2">
                    <Card className="border-slate-800 bg-slate-950/50 md:col-span-2">
                        <CardHeader>
                            <div className="flex items-center gap-2">
                                <GitBranch className="h-5 w-5 text-blue-500" />
                                <CardTitle className="text-white">System Architecture</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent className="text-sm text-slate-400 space-y-3">
                            <pre className="bg-slate-900/80 border border-slate-800 rounded-lg p-4 text-xs font-mono text-slate-300 overflow-x-auto">
{`LLM Agent (Claude/Cursor)
    |
    v
FastMCP 3.2  ←──  MCP HTTP SSE (:10807/mcp)
    |
    v
Docker MCP Server (FastAPI + FastMCP)
    ├── Tool Layer (container, image, volume, network tools)
    ├── REST API (:10807/api/*)
    ├── AI Bridge (:10807/api/chat -> Ollama/LM Studio)
    └── Docker SDK (named pipes -> Docker Desktop)
            |
            v
      Docker Desktop / Docker Engine (Windows)`}
                            </pre>
                            <p><strong>Dual transport:</strong> STDIO for Claude Desktop, HTTP SSE for web dashboard.</p>
                            <p><strong>Tauri desktop wrapper:</strong> Native Windows app (NSIS installer) with embedded PyInstaller backend.</p>
                        </CardContent>
                    </Card>

                    <Card className="border-slate-800 bg-slate-950/50">
                        <CardHeader>
                            <div className="flex items-center gap-2">
                                <Cpu className="h-5 w-5 text-cyan-500" />
                                <CardTitle className="text-white">Components</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent className="text-sm text-slate-400 space-y-2">
                            <ul className="list-disc ml-4 space-y-1">
                                <li><code className="text-blue-400">dockermcp/</code> — MCP tool modules (containers, images, volumes, networks, system)</li>
                                <li><code className="text-blue-400">docker_mcp/</code> — FastAPI web bridge, logging, AI router, auth</li>
                                <li><code className="text-blue-400">customization/</code> — Transport config, PyInstaller entry</li>
                                <li><code className="text-blue-400">web_sota/</code> — React 19 dashboard (Vite + Tailwind)</li>
                                <li><code className="text-blue-400">native/</code> — Tauri 2.0 wrapper + NSIS installer</li>
                            </ul>
                        </CardContent>
                    </Card>

                    <Card className="border-slate-800 bg-slate-950/50">
                        <CardHeader>
                            <div className="flex items-center gap-2">
                                <Wrench className="h-5 w-5 text-orange-500" />
                                <CardTitle className="text-white">Resilience: Triple Kill</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent className="text-sm text-slate-400 space-y-2">
                            <p>When Docker daemon hangs (OOM, WSL2 memory pressure, named pipe degradation):</p>
                            <ol className="list-decimal ml-4 space-y-1 text-xs">
                                <li>Kill <code className="text-blue-400">Docker Desktop.exe</code></li>
                                <li>Kill <code className="text-blue-400">com.docker.backend.exe</code></li>
                                <li>Kill <code className="text-blue-400">vpnkit.exe</code></li>
                                <li>Restart Docker Desktop, wait up to 90s</li>
                            </ol>
                            <p className="mt-2">Triggered via <strong>Restart Docker</strong> button on dashboard or <code className="text-blue-400">POST /api/docker/recover</code>.</p>
                        </CardContent>
                    </Card>
                </div>
            )}

            {activeTab === "usage" && (
                <div className="grid gap-6 md:grid-cols-2">
                    <Card className="border-slate-800 bg-slate-950/50">
                        <CardHeader>
                            <div className="flex items-center gap-2">
                                <Book className="h-5 w-5 text-blue-500" />
                                <CardTitle className="text-white">Quick Start</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent className="text-sm text-slate-400 space-y-3">
                            <p>1. Ensure Docker Desktop or Docker Engine is running.</p>
                            <p>2. Verify your user has permissions to access the Docker socket (named pipe).</p>
                            <p>3. Use <strong>AI Command</strong> page to issue natural language commands like <em>"List all containers"</em> or <em>"Restart the web proxy"</em>.</p>
                            <p>4. Use the <strong>Containers</strong> and <strong>Images</strong> pages for manual operations.</p>
                            <p>5. If the daemon hangs, click <strong>Restart Docker</strong> on the dashboard.</p>
                        </CardContent>
                    </Card>

                    <Card className="border-slate-800 bg-slate-950/50">
                        <CardHeader>
                            <div className="flex items-center gap-2">
                                <MessageSquare className="h-5 w-5 text-emerald-500" />
                                <CardTitle className="text-white">AI Command Examples</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent className="text-sm text-slate-400 space-y-2">
                            <p>Try these natural language commands in the AI Command page:</p>
                            <ul className="space-y-1.5 ml-4 list-disc text-xs">
                                <li><em>"List all running containers"</em></li>
                                <li><em>"Show me container logs for nginx"</em></li>
                                <li><em>"Restart the database container"</em></li>
                                <li><em>"What images do I have?"</em></li>
                                <li><em>"Check Docker daemon health"</em></li>
                                <li><em>"Clean up unused images and volumes"</em></li>
                            </ul>
                        </CardContent>
                    </Card>

                    <Card className="border-slate-800 bg-slate-950/50">
                        <CardHeader>
                            <div className="flex items-center gap-2">
                                <Wrench className="h-5 w-5 text-orange-500" />
                                <CardTitle className="text-white">MCP Tools</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent className="text-sm text-slate-400 space-y-2">
                            <p><strong>Available tool categories:</strong></p>
                            <ul className="space-y-1 ml-4 list-disc text-xs">
                                <li><code className="text-blue-400">container_*</code> — List, start, stop, restart, logs, exec</li>
                                <li><code className="text-blue-400">image_*</code> — List, pull, build, prune, tag</li>
                                <li><code className="text-blue-400">volume_*</code> — List, create, remove, prune</li>
                                <li><code className="text-blue-400">network_*</code> — List, create, connect, disconnect</li>
                                <li><code className="text-blue-400">system_*</code> — Info, disk usage, events</li>
                                <li><code className="text-blue-400">docker_daemon_*</code> — Daemon health, recover, restart, update</li>
                                <li><code className="text-blue-400">docker_desktop_*</code> — Desktop status, GPU info, GPU containers</li>
                                <li><code className="text-blue-400">agentic_*</code> — Multi-step LLM-planned workflows</li>
                            </ul>
                            <p className="text-xs text-slate-500 mt-2">Full list on the Tools page.</p>
                        </CardContent>
                    </Card>

                    <Card className="border-slate-800 bg-slate-950/50">
                        <CardHeader>
                            <div className="flex items-center gap-2">
                                <AlertCircle className="h-5 w-5 text-red-500" />
                                <CardTitle className="text-white">Troubleshooting</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent className="text-sm text-slate-400 space-y-2 text-xs">
                            <p><strong>"Failed to fetch" in dashboard:</strong> Check Docker is running and the backend port 10807 is not blocked. Click Restart Docker.</p>
                            <p><strong>"Docker daemon not available":</strong> Docker Desktop may be hung. Use the Restart Docker button on the dashboard or restart Docker Desktop manually.</p>
                            <p><strong>Containers show 0:</strong> Docker Desktop is running but the named pipe connection failed. Run <code className="text-blue-400">docker ps</code> in terminal to verify.</p>
                            <p><strong>Backend won't start:</strong> Check <code className="text-blue-400">%LOCALAPPDATA%\Docker MCP\logs\</code> for error details.</p>
                        </CardContent>
                    </Card>
                </div>
            )}

            {activeTab === "docker" && (
                <div className="grid gap-6 md:grid-cols-2">
                    <Card className="border-slate-800 bg-slate-950/50">
                        <CardHeader>
                            <div className="flex items-center gap-2">
                                <Server className="h-5 w-5 text-blue-500" />
                                <CardTitle className="text-white">Docker Desktop Requirements</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent className="text-sm text-slate-400 space-y-2">
                            <ul className="list-disc ml-4 space-y-1">
                                <li>Docker Desktop 4.x+ for Windows (WSL2 backend recommended)</li>
                                <li>Named pipe connection: <code className="text-blue-400">\\.\pipe\docker_engine</code></li>
                                <li>Minimum 8GB RAM allocated to Docker (12GB+ for AI workloads)</li>
                                <li>User must be in the <code className="text-blue-400">docker-users</code> group</li>
                            </ul>
                        </CardContent>
                    </Card>

                    <Card className="border-slate-800 bg-slate-950/50">
                        <CardHeader>
                            <div className="flex items-center gap-2">
                                <AlertCircle className="h-5 w-5 text-red-500" />
                                <CardTitle className="text-white">Daemon Hang Detection</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent className="text-sm text-slate-400 space-y-2">
                            <p><strong>Symptoms:</strong></p>
                            <ul className="space-y-1 ml-4 list-disc text-xs">
                                <li><code className="text-blue-400">docker ps</code> hangs or times out</li>
                                <li>Containers randomly exit with code 137 (OOM)</li>
                                <li>GUI slow, high CPU/memory</li>
                                <li>LLM inference stops responding</li>
                            </ul>
                            <p className="mt-2"><strong>Fix:</strong> Click <strong>Restart Docker</strong> on dashboard or call <code className="text-blue-400">docker_desktop_status(autofix=true)</code>.</p>
                        </CardContent>
                    </Card>

                    <Card className="border-slate-800 bg-slate-950/50">
                        <CardHeader>
                            <div className="flex items-center gap-2">
                                <Cpu className="h-5 w-5 text-cyan-500" />
                                <CardTitle className="text-white">Docker Management Tools</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent className="text-sm text-slate-400 space-y-2">
                            <p><strong>Daemon management MCP tools:</strong></p>
                            <ul className="space-y-1 ml-4 list-disc text-xs">
                                <li><code className="text-blue-400">docker_desktop_status</code> — Daemon health, images, containers, resources, auto-recover</li>
                                <li><code className="text-blue-400">docker_daemon_recover</code> — Emergency recovery (triple kill)</li>
                                <li><code className="text-blue-400">docker_daemon_restart</code> — Graceful restart</li>
                                <li><code className="text-blue-400">docker_desktop_update</code> — Fix elevation, clear temp</li>
                            </ul>
                        </CardContent>
                    </Card>

                    <Card className="border-slate-800 bg-slate-950/50">
                        <CardHeader>
                            <div className="flex items-center gap-2">
                                <Zap className="h-5 w-5 text-yellow-500" />
                                <CardTitle className="text-white">AI Workload Optimization</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent className="text-sm text-slate-400 space-y-2 text-xs">
                            <ul className="space-y-1 ml-4 list-disc">
                                <li>Set resource limits in docker-compose.yml</li>
                                <li>Configure log rotation to prevent 50GB+ log bloat</li>
                                <li>Increase Docker Desktop memory to 12GB+</li>
                                <li>Use <code className="text-blue-400">docker_desktop_status(autofix=true)</code> for auto-recovery</li>
                                <li>Run weekly: <code className="text-blue-400">just docker-fix</code></li>
                            </ul>
                            <p className="text-xs text-slate-500 mt-2">See: DOCKER_DAEMON_AI_WORKLOADS.md</p>
                        </CardContent>
                    </Card>

                    <Card className="border-slate-800 bg-slate-950/50 md:col-span-2">
                        <CardHeader>
                            <div className="flex items-center gap-2">
                                <HelpCircle className="h-5 w-5 text-cyan-500" />
                                <CardTitle className="text-white">Ports & Fleet Integration</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent className="text-sm text-slate-400">
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                {[
                                    { port: "10807", service: "Backend (FastAPI + MCP HTTP)", proto: "HTTP" },
                                    { port: "10806", service: "Frontend (Vite dev)", proto: "HTTP" },
                                    { port: "11434", service: "Ollama (local LLM)", proto: "HTTP" },
                                    { port: "1234", service: "LM Studio (local LLM)", proto: "HTTP" },
                                ].map((s) => (
                                    <div key={s.port} className="bg-slate-900/60 rounded-lg p-3 border border-slate-800">
                                        <div className="text-xs text-slate-500">{s.service}</div>
                                        <div className="text-sm font-mono text-slate-200 mt-1">{s.port}</div>
                                    </div>
                                ))}
                            </div>
                            <p className="text-xs text-slate-500 mt-3">Ports registered in mcp-central-docs/operations/WEBAPP_PORTS.md</p>
                        </CardContent>
                    </Card>
                </div>
            )}
        </div>
    );
}
