# ---------- Base ----------
FROM python:3.11-slim

# ---------- System setup ----------
RUN apt-get update && apt-get install -y \
    sudo \
    tini \
    git \
    vim \
    build-essential \
    curl \
    libcurl4-openssl-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# ---------- Install Node.js ----------
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

WORKDIR /srv/jupyterhub

# ---------- Python packages ----------
RUN pip install --no-cache-dir \
    jupyterhub \
    jupyterlab \
    notebook \
    jupyterhub-idle-culler \
    pycurl

# ---------- Install configurable-http-proxy ----------
RUN npm install -g configurable-http-proxy

# ---------- Create example users ----------
# Set root password for JupyterHub admin access
RUN echo "root:admin" | chpasswd
RUN mkdir -p /home/root && chown root:root /home/root

# ---------- Configure sudo restrictions ----------
# Allow sudo users to run most commands but restrict user management
RUN echo "# Allow sudo group to run most commands" >> /etc/sudoers && \
    echo "%sudo ALL=(ALL) ALL" >> /etc/sudoers && \
    echo "# Restrict user management commands (except for root)" >> /etc/sudoers && \
    echo "%sudo ALL=!/usr/sbin/useradd,!/usr/sbin/userdel,!/usr/sbin/usermod,!/usr/sbin/adduser,!/usr/sbin/deluser,!/usr/bin/passwd [a-zA-Z]*" >> /etc/sudoers && \
    echo "root ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# ---------- Copy JupyterHub config and templates ----------
COPY jupyterhub_config.py /srv/jupyterhub/jupyterhub_config.py
COPY templates/ /srv/jupyterhub/templates/

# ---------- Expose and run ----------
EXPOSE 8000
CMD ["tini", "--", "jupyterhub", "-f", "/srv/jupyterhub/jupyterhub_config.py"]
