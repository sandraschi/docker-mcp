# Docker MCP Monitoring Stack

This directory contains the configuration for the Docker MCP monitoring stack, which includes:

- **Loki**: Log aggregation system
- **Promtail**: Log collector
- **Grafana**: Visualization and alerting
- **Prometheus**: Metrics collection
- **Backup**: Automated backup system

## Prerequisites

- Docker and Docker Compose
- `make` utility (optional, for convenience commands)

## Configuration

### Option 1: Automatic Setup (Recommended)

Run the setup script to generate a secure `.env` file:

```bash
# Windows
.\setup-env.bat

# Linux/macOS
chmod +x setup-env.sh
./setup-env.sh
```

The script will:

- Generate secure random passwords
- Create a properly formatted `.env` file
- Preserve existing values if `.env` already exists

### Option 2: Manual Setup

1. Copy `.env.example` to `.env`:

   ```bash
   copy .env.example .env  # Windows
   # or
   cp .env.example .env    # Linux/macOS
   ```

2. Edit the `.env` file with your configuration:
   - Set `GRAFANA_ADMIN_PASSWORD` to a secure password
   - Configure email alerts (optional)
   - Update any other settings as needed

## Starting the Stack

```bash
docker-compose -f ../docker-compose-monitoring.yml up -d
```

## Accessing Services

- **Grafana**: `http://localhost:3000`
  - Default username: `admin`
  - Password: Set in `.env` as `GRAFANA_ADMIN_PASSWORD`

- **Prometheus**: `http://localhost:9090`
- **Loki**: `http://localhost:3100`

## Backup System

Backups run daily at 2 AM and are stored in the `backup_data` volume. The backup includes:

- Grafana configuration and dashboards
- Prometheus data
- Loki logs

### Manual Backup

To create a manual backup:

```bash
docker-compose -f ../docker-compose-monitoring.yml exec backup /backup.sh
```

## Monitoring Configuration

### Logging

- Logs are collected from `/var/log/dockermcp/*.log` by Promtail
- Logs are stored in Loki with labels for filtering

### Metrics

- Prometheus scrapes metrics from the Docker MCP application
- Default scrape interval: 15s

### Alerts

Configure alerts in Grafana using the web interface. Example alert rules are included in the provisioning directory.

## Troubleshooting

### View Logs

```bash
docker-compose -f ../docker-compose-monitoring.yml logs -f
```

### Check Service Status

```bash
docker-compose -f ../docker-compose-monitoring.yml ps
```

## Cleanup

To stop and remove all monitoring containers and volumes:

```bash
docker-compose -f ../docker-compose-monitoring.yml down -v
```

## Security Notes

- Always use strong passwords in production
- Restrict access to the monitoring ports (3000, 9090, 3100)
- Regularly update container images to the latest versions
