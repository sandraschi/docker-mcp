# Per-repo fleet start config for docker-mcp
# Edit ports/backend target here - start.ps1 is fleet-standard.
@{
    Name         = 'docker-mcp'
    BackendPort  = 10807
    FrontendPort = 10806
    HealthPath   = '/api/health'
    WebRoot      = 'D:\Dev\repos\docker-mcp\web_sota'
    Backend = @{
        Kind          = 'uvicorn-web-app'
        UvicornTarget = 'server:web_app'
        SyncExtras    = @('dev')
        Env           = @{ WEB_PORT = '10807' }
    }
    Frontend = @{
        Kind           = 'vite-npm'
        PackageManager = 'npm'
        PortEnvVar     = 'VITE_PORT'
        ApiTargetEnv   = 'VITE_API_TARGET'
    }
}
