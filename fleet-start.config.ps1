# Per-repo fleet start config for docker-mcp
# Edit ports/backend target here - start.ps1 is fleet-standard.
@{
    Name         = 'docker-mcp'
    BackendPort  = 10807
    FrontendPort = 10806
    HealthPath   = '/api/health'
    WebRoot      = 'web_sota'
    Backend = @{
        Kind          = 'uvicorn'
        UvicornTarget = 'customization.server:app'
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
