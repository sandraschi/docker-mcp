@echo off
setlocal enabledelayedexpansion

:: Check if .env already exists
if exist ".env" (
    echo Warning: .env file already exists.
    set /p OVERWRITE=Do you want to overwrite it? (y/N) 
    if /i not "!OVERWRITE!"=="y" (
        echo Aborting. No changes were made.
        exit /b 0
    )
)

:: Generate secure values if not provided by environment
if "%GRAFANA_ADMIN_PASSWORD%"=="" (
    for /f "usebackq" %%i in (`powershell -Command "-join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | %% {[char]%%_})"`) do set GRAFANA_ADMIN_PASSWORD=%%i
)

if "%GRAFANA_SECRET_KEY%"=="" (
    for /f "usebackq" %%i in (`powershell -Command "-join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | %% {[char]%%_})"`) do set GRAFANA_SECRET_KEY=%%i
)

:: Create the .env file
echo # ==================================== > .env
echo # Docker MCP Monitoring Configuration >> .env
echo # Auto-generated on %date% %time% >> .env
echo # ==================================== >> .env
echo. >> .env
echo # ----------------------------- >> .env
echo # Grafana Configuration >> .env
echo # ----------------------------- >> .env
echo GRAFANA_ADMIN_PASSWORD=!GRAFANA_ADMIN_PASSWORD! >> .env
echo GRAFANA_SECRET_KEY=!GRAFANA_SECRET_KEY! >> .env
echo. >> .env
echo # ----------------------------- >> .env
echo # Email Alert Configuration >> .env
echo # ----------------------------- >> .env
echo SMTP_ENABLED=false >> .env
echo SMTP_HOST=smtp.office365.com >> .env
echo SMTP_PORT=587 >> .env
echo SMTP_USER=alerts@yourdomain.com >> .env
echo SMTP_PASSWORD=your_smtp_password >> .env
echo SMTP_FROM=alerts@yourdomain.com >> .env
echo SMTP_FROM_NAME="Docker MCP Alerts" >> .env
echo SMTP_STARTTLS_POLICY=OpportunisticStartTLS >> .env
echo. >> .env
echo # ----------------------------- >> .env
echo # Loki Configuration >> .env
echo # ----------------------------- >> .env
echo # For Docker Compose environment: >> .env
echo LOKI_URL=http://loki:3100 >> .env
echo. >> .env
echo # For external Loki or local development: >> .env
echo # LOKI_URL=http://localhost:3100 >> .env
echo. >> .env
echo # ----------------------------- >> .env
echo # Alert Recipients >> .env
echo # ----------------------------- >> .env
echo ALERT_EMAIL_ADMIN=admin@yourdomain.com >> .env
echo ALERT_EMAIL_DEVOPS=devops@yourdomain.com >> .env
echo. >> .env
echo # ----------------------------- >> .env
echo # Environment Configuration >> .env
echo # ----------------------------- >> .env
echo ENVIRONMENT=development >> .env
echo LOG_RETENTION_HOURS=720 >> .env
echo. >> .env
echo # ----------------------------- >> .env
echo # Backup Configuration >> .env
echo # ----------------------------- >> .env
echo BACKUP_RETENTION_DAYS=7 >> .env
echo BACKUP_SCHEDULE=^"0 2 * * *^" >> .env
echo. >> .env
echo # ----------------------------- >> .env
echo # Resource Limits >> .env
echo # ----------------------------- >> .env
echo GRAFANA_MEMORY_LIMIT=512M >> .env
echo PROMETHEUS_MEMORY_LIMIT=1G >> .env
echo LOKI_MEMORY_LIMIT=1G >> .env
echo. >> .env
echo # ----------------------------- >> .env
echo # Security Settings >> .env
echo # ----------------------------- >> .env
echo ENABLE_HTTPS=false >> .env
echo # SSL_CERT_PATH=./certs/fullchain.pem >> .env
echo # SSL_KEY_PATH=./certs/privkey.pem >> .env

echo.
echo .env file has been created with secure defaults.
echo Please review and edit the .env file to configure your setup.

endlocal
