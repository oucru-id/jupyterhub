ARG JUPYTERHUB_VERSION
FROM quay.io/jupyterhub/jupyterhub:$JUPYTERHUB_VERSION

RUN apt-get update -y && apt-get install -y libpam-dev python3-dev build-essential sudo

COPY --chown=root:root sudoconfig /etc/sudoers.d/sudoconfig

RUN python3 -m pip install --no-cache-dir \
    jupyterlab \
    jupyterhub-nativeauthenticator \
    jupyterhub-idle-culler