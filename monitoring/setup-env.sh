#!/bin/bash

# Check if .env already exists
if [ -f ".env" ]; then
    echo "Warning: .env file already exists. Do you want to overwrite it? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Aborting. No changes were made."
        exit 0
    fi
fi

# Generate a secure Grafana admin password if not set
if [ -z "$GRAFANA_ADMIN_PASSWORD" ]; then
    GRAFANA_ADMIN_PASSWORD=$(openssl rand -hex 16)
fi

# Generate a secure secret key if not set
if [ -z "$GRAFANA_SECRET_KEY" ]; then
    GRAFANA_SECRET_KEY=$(openssl rand -hex 16)
fi

# Create the .env file with the generated values
cat > .env <<EOL
# ====================================
# Docker MCP Monitoring Configuration
# Auto-generated on $(date)
# ====================================

# -----------------------------
# Grafana Configuration
# -----------------------------
GRAFANA_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
GRAFANA_SECRET_KEY=${GRAFANA_SECRET_KEY}

# -----------------------------
# Email Alert Configuration
# -----------------------------
SMTP_ENABLED=false
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=alerts@yourdomain.com
SMTP_PASSWORD=your_smtp_password
SMTP_FROM=alerts@yourdomain.com
SMTP_FROM_NAME="Docker MCP Alerts"
SMTP_STARTTLS_POLICY=OpportunisticStartTLS

# -----------------------------
# Loki Configuration
# -----------------------------
# For Docker Compose environment:
LOKI_URL=http://loki:3100

# For external Loki or local development:
# LOKI_URL=http://localhost:3100

# -----------------------------
# Alert Recipients
# -----------------------------
ALERT_EMAIL_ADMIN=admin@yourdomain.com
ALERT_EMAIL_DEVOPS=devops@yourdomain.com

# -----------------------------
# Environment Configuration
# -----------------------------
ENVIRONMENT=development
LOG_RETENTION_HOURS=720

# -----------------------------
# Backup Configuration
# -----------------------------
BACKUP_RETENTION_DAYS=7
BACKUP_SCHEDULE="0 2 * * *"

# -----------------------------
# Resource Limits
# -----------------------------
GRAFANA_MEMORY_LIMIT=512M
PROMETHEUS_MEMORY_LIMIT=1G
LOKI_MEMORY_LIMIT=1G

# -----------------------------
# Security Settings
# -----------------------------
ENABLE_HTTPS=false
# SSL_CERT_PATH=./certs/fullchain.pem
# SSL_KEY_PATH=./certs/privkey.pem
EOL

echo ".env file has been created with secure defaults."
echo "Please review and edit the .env file to configure your setup."
