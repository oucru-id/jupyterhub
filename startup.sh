#!/bin/bash

# Startup script for JupyterHub with persistent user accounts

# Store backups in persisted data volume
BACKUP_DIR="/srv/jupyterhub/data/system-backup"

# Function to backup system files
backup_system_files() {
    echo "Backing up system files to $BACKUP_DIR..."
    mkdir -p "$BACKUP_DIR"
    
    # Backup user account files
    cp /etc/passwd "$BACKUP_DIR/passwd" 2>/dev/null || true
    cp /etc/shadow "$BACKUP_DIR/shadow" 2>/dev/null || true
    cp /etc/group "$BACKUP_DIR/group" 2>/dev/null || true
    cp /etc/gshadow "$BACKUP_DIR/gshadow" 2>/dev/null || true
}

# Function to restore system files
restore_system_files() {
    echo "Restoring system files from $BACKUP_DIR..."
    
    if [ -f "$BACKUP_DIR/passwd" ]; then
        echo "Restoring user accounts..."
        
        # Merge existing users with backed up users
        # Keep system users (UID < 1000) from current /etc/passwd
        # Add regular users (UID >= 1000) from backup
        
        # Create temporary files
        TEMP_PASSWD="/tmp/passwd.new"
        TEMP_SHADOW="/tmp/shadow.new"
        TEMP_GROUP="/tmp/group.new"
        TEMP_GSHADOW="/tmp/gshadow.new"
        
        # Start with system users (UID < 1000)
        awk -F: '$3 < 1000' /etc/passwd > "$TEMP_PASSWD"
        awk -F: '$3 < 1000' /etc/shadow > "$TEMP_SHADOW"
        awk -F: '$3 < 1000' /etc/group > "$TEMP_GROUP"
        awk -F: '$3 < 1000' /etc/gshadow > "$TEMP_GSHADOW"
        
        # Add regular users from backup (UID >= 1000)
        if [ -f "$BACKUP_DIR/passwd" ]; then
            awk -F: '$3 >= 1000' "$BACKUP_DIR/passwd" >> "$TEMP_PASSWD"
        fi
        if [ -f "$BACKUP_DIR/shadow" ]; then
            awk -F: '$3 >= 1000' "$BACKUP_DIR/shadow" >> "$TEMP_SHADOW"
        fi
        if [ -f "$BACKUP_DIR/group" ]; then
            awk -F: '$3 >= 1000' "$BACKUP_DIR/group" >> "$TEMP_GROUP"
        fi
        if [ -f "$BACKUP_DIR/gshadow" ]; then
            awk -F: '$3 >= 1000' "$BACKUP_DIR/gshadow" >> "$TEMP_GSHADOW"
        fi
        
        # Replace system files with merged versions
        mv "$TEMP_PASSWD" /etc/passwd
        mv "$TEMP_SHADOW" /etc/shadow
        mv "$TEMP_GROUP" /etc/group
        mv "$TEMP_GSHADOW" /etc/gshadow
        
        # Set proper permissions
        chmod 644 /etc/passwd /etc/group
        chmod 640 /etc/shadow /etc/gshadow
        chown root:root /etc/passwd /etc/shadow /etc/group /etc/gshadow
        chgrp shadow /etc/shadow /etc/gshadow
        
        echo "User accounts restored successfully."
    else
        echo "No backup found, starting fresh."
    fi
}

# Function to setup backup on exit
setup_backup_on_exit() {
    # Create a trap to backup files when container stops
    trap 'backup_system_files' EXIT TERM INT
}

# Main startup sequence
echo "Starting JupyterHub with persistent user accounts..."

# Restore user accounts from previous runs
restore_system_files

# Setup backup on container exit
setup_backup_on_exit

# Start JupyterHub
echo "Starting JupyterHub..."
exec tini -- jupyterhub -f /srv/jupyterhub/jupyterhub_config.py