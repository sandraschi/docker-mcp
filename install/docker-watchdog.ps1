# Docker Watchdog Service - Windows Installation
# Run this script as Administrator

$serviceName = "DockerWatchdog"
$pythonPath = (Get-Command python).Source
$scriptPath = Join-Path $PSScriptRoot "..\src\dockermcp\services\docker_watchdog.py"
$serviceDisplayName = "Docker Watchdog Service"
$serviceDescription = "Monitors and automatically recovers the Docker daemon"

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Error "This script must be run as Administrator"
    exit 1
}

# Create the service if it doesn't exist
if (-not (Get-Service $serviceName -ErrorAction SilentlyContinue)) {
    $service = New-Service -Name $serviceName \
                          -DisplayName $serviceDisplayName \
                          -BinaryPathName "`"$pythonPath`" `"$scriptPath`"" \
                          -Description $serviceDescription \
                          -StartupType Automatic \
                          -ErrorAction Stop
    
    Write-Host "Service '$serviceName' created successfully"
} else {
    Write-Host "Service '$serviceName' already exists"
}

# Configure service recovery options
$sc = "sc.exe"
& $sc failure $serviceName reset= 86400 actions= restart/60000/restart/60000/restart/60000
& $sc failureflag $serviceName 1

# Set service to auto-start
Set-Service -Name $serviceName -StartupType Automatic

# Start the service
Start-Service -Name $serviceName -ErrorAction Stop

Write-Host "Docker Watchdog service installed and started successfully"
Write-Host "Service will automatically restart Docker if it becomes unresponsive"
Write-Host "Logs are written to: $PWD\docker_watchdog.log"
