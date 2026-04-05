import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { HelpCircle, Book, Shield, Zap, Info, AlertCircle, Wrench } from "lucide-react";

export function Help() {
    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-2xl font-bold tracking-tight text-white">Help & Documentation</h2>
                <p className="text-slate-400">Reference guide for Docker MCP Server with Desktop Management</p>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
                <Card className="border-slate-800 bg-slate-950/50">
                    <CardHeader>
                        <div className="flex items-center gap-2">
                            <Book className="h-5 w-5 text-blue-500" />
                            <CardTitle className="text-white">Quick Start</CardTitle>
                        </div>
                    </CardHeader>
                    <CardContent className="text-sm text-slate-400 space-y-4">
                        <p>1. Ensure Docker Desktop or Docker Engine is running.</p>
                        <p>2. Verify that your user has permissions to access the Docker socket.</p>
                        <p>3. Use the AI Command page to issue commands like "List all containers" or "Restart the web proxy".</p>
                        <p>4. Check daemon health via Docker Desktop tools (see below).</p>
                    </CardContent>
                </Card>

                <Card className="border-slate-800 bg-slate-950/50">
                    <CardHeader>
                        <div className="flex items-center gap-2">
                            <Wrench className="h-5 w-5 text-orange-500" />
                            <CardTitle className="text-white">Docker Desktop Tools (NEW)</CardTitle>
                        </div>
                    </CardHeader>
                    <CardContent className="text-sm text-slate-400 space-y-4">
                        <p><strong>Native MCP tools for Docker daemon management:</strong></p>
                        <ul className="space-y-2 ml-4 list-disc">
                            <li><code className="text-blue-400">docker_desktop_status</code> — Check daemon health, list images/containers, monitor resources, auto-recover from hangs</li>
                            <li><code className="text-blue-400">docker_daemon_recover</code> — Emergency recovery from hung daemon</li>
                            <li><code className="text-blue-400">docker_daemon_restart</code> — Graceful daemon restart</li>
                            <li><code className="text-blue-400">docker_desktop_update</code> — Fix elevation errors, clear temp folders</li>
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
                    <CardContent className="text-sm text-slate-400 space-y-4">
                        <p><strong>Hanging Daemon Symptoms:</strong></p>
                        <ul className="space-y-1 ml-4 list-disc text-xs">
                            <li>`docker ps` hangs or times out</li>
                            <li>Containers randomly exit with code 137 (OOM)</li>
                            <li>GUI becomes slow, high CPU/memory usage</li>
                            <li>LLM inference stops responding</li>
                        </ul>
                        <p className="mt-3"><strong>Quick Fix:</strong> Call `docker_desktop_status(autofix=true)` to auto-recover.</p>
                    </CardContent>
                </Card>

                <Card className="border-slate-800 bg-slate-950/50">
                    <CardHeader>
                        <div className="flex items-center gap-2">
                            <Shield className="h-5 w-5 text-purple-500" />
                            <CardTitle className="text-white">Security & Auth</CardTitle>
                        </div>
                    </CardHeader>
                    <CardContent className="text-sm text-slate-400 space-y-4">
                        <p>Web access requires Basic Authentication. Default credentials are s:sandra p:sandra123.</p>
                        <p>The Docker socket is accessed locally only; ensure your environment is secure.</p>
                        <p>Resource limits recommended for AI workloads: 12GB+ memory, 4+ CPUs.</p>
                    </CardContent>
                </Card>

                <Card className="border-slate-800 bg-slate-950/50">
                    <CardHeader>
                        <div className="flex items-center gap-2">
                            <Zap className="h-5 w-5 text-yellow-500" />
                            <CardTitle className="text-white">MCP Parameters</CardTitle>
                        </div>
                    </CardHeader>
                    <CardContent className="text-sm text-slate-400 space-y-4">
                        <p><strong>Server Configuration:</strong></p>
                        <ul className="space-y-1 ml-4 list-disc text-xs">
                            <li>Port: 10803 (Docker MCP)</li>
                            <li>FastMCP Version: 3.1+</li>
                            <li>Transport: Dual (STDIO + HTTP Bridge)</li>
                            <li>Base URL: /api/v1</li>
                            <li>Python: 3.12+</li>
                        </ul>
                    </CardContent>
                </Card>

                <Card className="border-slate-800 bg-slate-950/50">
                    <CardHeader>
                        <div className="flex items-center gap-2">
                            <Info className="h-5 w-5 text-emerald-500" />
                            <CardTitle className="text-white">About This Server</CardTitle>
                        </div>
                    </CardHeader>
                    <CardContent className="text-sm text-slate-400 space-y-4">
                        <p>Docker MCP Server with comprehensive Docker operations and Desktop daemon management.</p>
                        <p className="text-xs">Part of the Sandra SOTA Fleet (January 2026). Standardized UI, dual transport mode, and AI-driven container orchestration with hang detection and auto-recovery.</p>
                    </CardContent>
                </Card>

                <Card className="border-slate-800 bg-slate-950/50 md:col-span-2">
                    <CardHeader>
                        <div className="flex items-center gap-2">
                            <HelpCircle className="h-5 w-5 text-cyan-500" />
                            <CardTitle className="text-white">AI Workload Optimization</CardTitle>
                        </div>
                    </CardHeader>
                    <CardContent className="text-sm text-slate-400 space-y-3">
                        <p><strong>For LLM inference (Ollama, Gemma, etc.):</strong></p>
                        <ul className="space-y-2 ml-4 list-disc">
                            <li>Set resource limits in docker-compose.yml (CPU/memory hard limits + reservations)</li>
                            <li>Configure log rotation to prevent 50GB+ log file bloat</li>
                            <li>Increase Docker Desktop memory to 12GB+ (Settings {'>'} Resources {'>'} Memory)</li>
                            <li>Use Gemma 2 27B for SOTA quality (25-30 tokens/sec on RTX 4090)</li>
                            <li>Use <code className="text-blue-400">docker_desktop_status(autofix=true)</code> for automatic hang recovery</li>
                            <li>Run weekly cleanup: <code className="text-blue-400">fix-docker-daemon.ps1</code> or <code className="text-blue-400">just docker-fix</code></li>
                        </ul>
                        <p className="text-xs text-slate-500 mt-2">See docs: DOCKER_DAEMON_AI_WORKLOADS.md, OLLAMA_GEMMA_SETUP.md</p>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
