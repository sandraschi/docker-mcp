#!/bin/bash

# Configuration
BACKUP_DIR="/backups/monitoring"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/monitoring_backup_$TIMESTAMP.tar.gz"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Create backup
tar -czf "$BACKUP_FILE" \
  /var/lib/grafana \
  /var/lib/prometheus \
  /loki \
  /etc/grafana/provisioning \
  /etc/prometheus/prometheus.yml

# Keep only the last 7 backups
find "$BACKUP_DIR" -name "monitoring_backup_*.tar.gz" -type f | sort -r | tail -n +8 | xargs rm -f

echo "Backup created: $BACKUP_FILE"
