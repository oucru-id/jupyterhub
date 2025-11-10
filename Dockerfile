ARG JUPYTERHUB_VERSION
FROM quay.io/jupyterhub/jupyterhub:$JUPYTERHUB_VERSION

RUN apt-get update -y && apt-get install -y libpam-dev python3-dev build-essential sudo git

COPY --chown=root:root sudoconfig /etc/sudoers.d/sudoconfig

RUN apt-get update -y && apt-get install -y ca-certificates curl
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
RUN apt-get install -y nodejs
RUN python3 -m pip install --no-cache-dir \
     jupyterlab \
     jupyterhub-nativeauthenticator \
     jupyterhub-idle-culler \
     jupyterlab-git \
     jupyterlab-code-formatter \
     jupyterlab-search-replace \
     jupyterlab-day \
     jupyterlab-night \
     jupyterlab-lsp==5.2.0 \
     jedi-language-server
RUN git config --system credential.helper 'store --file ~/.git-credentials'
RUN jupyter lab build --dev-build=False --minimize=False