#!/bin/bash
set -e

if [ -n "$ADMIN_USER" ] && [ -n "$ADMIN_PASSWORD" ]; then
  # Create the admin user with a home directory
  if ! id -u "$ADMIN_USER" >/dev/null 2>&1; then
    echo "Creating admin user: $ADMIN_USER"
    useradd -m -s /bin/bash "$ADMIN_USER"
    echo "$ADMIN_USER:$ADMIN_PASSWORD" | chpasswd
    # Add to sudo group for admin privileges within the container
    usermod -aG sudo "$ADMIN_USER"
  fi
fi

# Execute the original JupyterHub entrypoint
exec jupyterhub -f /srv/jupyterhub/jupyterhub_config.py