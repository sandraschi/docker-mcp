# Docker MCP Monitoring Stack

This directory contains the configuration for the Docker MCP monitoring stack, which includes:

- **Grafana** - Visualization and dashboards
- **Loki** - Log aggregation
- **Prometheus** - Metrics collection
- **Backup** - Automated backups

## Prerequisites

1. Docker and Docker Compose installed
2. SMTP credentials for email alerts
3. At least 4GB of free disk space
4. At least 2GB of free memory

## Quick Start

1. Copy the example environment file and update with your settings:
   ```bash
   cp monitoring/.env.example .env
   # Edit .env with your configuration
   ```

2. Start the monitoring stack:
   ```bash
   docker-compose -f docker-compose-monitoring.yml up -d
   ```

3. Access the services:
   - Grafana: http://localhost:3000
     - Default credentials: admin/admin (change on first login)
   - Prometheus: http://localhost:9090
   - Loki: http://localhost:3100

## Configuration

### Email Alerts

Update the following in your `.env` file:

```ini
# SMTP Configuration for Alerts
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=your-email@example.com
SMTP_PASSWORD=your-smtp-password
SMTP_FROM=your-email@example.com
SMTP_FROM_NAME="Docker MCP Alerts"

# Alert Recipients
ALERT_EMAIL_SANDRASCHIPAL=sandraschipal@hotmail.com
```

### Backup Configuration

Backups run daily at 2 AM and are stored in the `backup_data` volume. To restore from a backup:

1. Find the backup file in the volume:
   ```bash
   docker run --rm -v dockermcp_backup_data:/backup -it alpine ls -la /backup/monitoring
   ```

2. Restore the backup:
   ```bash
   # Stop the monitoring stack first
   docker-compose -f docker-compose-monitoring.yml down
   
   # Restore from backup
   docker run --rm -v dockermcp_backup_data:/backup -v dockermcp_grafana_data:/grafana -v dockermcp_prometheus_data:/prometheus -v dockermcp_loki_data:/loki -it alpine sh -c "tar -xzf /backup/monitoring/backup_20230101_020000.tar.gz -C /"
   
   # Start the stack again
   docker-compose -f docker-compose-monitoring.yml up -d
   ```

## Alerting

### Pre-configured Alerts

- **High Error Rate**: Triggered when error rate exceeds 5 errors per minute
- **Application Down**: Triggered when the application is down for more than 2 minutes
- **High CPU Usage**: Triggered when CPU usage exceeds 80% for 10 minutes
- **High Memory Usage**: Triggered when memory usage exceeds 85%
- **Low Disk Space**: Triggered when disk space is below 20%

### Customizing Alerts

Edit the alert rules in `monitoring/provisioning/alerting/alert-rules.yml` and restart the monitoring stack.

## Maintenance

### Upgrading

To upgrade the monitoring stack:

1. Stop the stack:
   ```bash
   docker-compose -f docker-compose-monitoring.yml down
   ```

2. Pull the latest images:
   ```bash
   docker-compose -f docker-compose-monitoring.yml pull
   ```

3. Start the stack again:
   ```bash
   docker-compose -f docker-compose-monitoring.yml up -d
   ```

### Monitoring Data Retention

- **Loki logs**: 30 days
- **Prometheus metrics**: 15 days
- **Grafana dashboards**: Stored in the database, included in backups

## Troubleshooting

### Check Logs

```bash
# Grafana logs
docker-compose -f docker-compose-monitoring.yml logs grafana

# Loki logs
docker-compose -f docker-compose-monitoring.yml logs loki

# Prometheus logs
docker-compose -f docker-compose-monitoring.yml logs prometheus
```

### Common Issues

1. **Email not sending**:
   - Check SMTP settings in `.env`
   - Verify network connectivity to SMTP server
   - Check Grafana logs for SMTP errors

2. **High resource usage**:
   - Adjust scrape intervals in `prometheus.yml`
   - Reduce log retention in `loki-config.yaml`

3. **Backup failures**:
   - Check available disk space
   - Verify backup script has execute permissions
   - Check cron logs in the backup container

## Security

1. Change default credentials
2. Enable HTTPS for Grafana
3. Restrict access to monitoring ports
4. Regularly update to the latest versions

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
