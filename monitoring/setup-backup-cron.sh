#!/bin/bash

# Create backup directory
mkdir -p /backups/monitoring

# Create a daily backup at 2 AM
echo "0 2 * * * root /backup.sh" > /etc/cron.d/monitoring-backup

# Set proper permissions
chmod 644 /etc/cron.d/monitoring-backup
chmod +x /backup.sh

# Start cron service
echo "Starting cron service..."
crond -f -L /var/log/cron.log
