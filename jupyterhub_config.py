# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

# Configuration file for JupyterHub
import os
import binascii
import nativeauthenticator

c = get_config()  # noqa: F821

# We rely on environment variables to configure JupyterHub so that we
# avoid having to rebuild the JupyterHub container every time we change a
# configuration parameter.

# Redirect users to hub home instead of auto-spawning servers
c.JupyterHub.redirect_to_server = True

# Spawn single-user servers locally
c.JupyterHub.spawner_class = 'jupyterhub.spawner.LocalProcessSpawner'

# Idle culler configuration
c.JupyterHub.load_roles = [
    {
        "name": "jupyterhub-idle-culler-role",
        "scopes": [
            "list:users",
            "read:users:activity",
            "read:servers",
            "delete:servers",
        ],
        "services": ["idle-culler"],
    }
]

c.JupyterHub.services = [
    {
        "name": "idle-culler",
        "command": [
            "python3",
            "-m",
            "jupyterhub_idle_culler",
            "--timeout=1800",
            "--cull-every=600",
        ],
    }
]

# User containers will access hub by container name on the Docker network
c.JupyterHub.hub_ip = "127.0.0.1"
c.JupyterHub.hub_port = 8080

# Persist hub data on volume mounted inside container
c.JupyterHub.cookie_secret = binascii.unhexlify(os.environ["JUPYTERHUB_COOKIE_SECRET"])
c.JupyterHub.db_url = "sqlite:////srv/jupyterhub/data/jupyterhub.sqlite"

# Allow all signed-up users to login
c.Authenticator.allow_all = True

# Authenticate users with Native Authenticator
c.JupyterHub.authenticator_class = 'native'
import pwd
import subprocess
def create_system_user(spawner):
    username = spawner.user.name
    try:
        pwd.getpwnam(username)
    except KeyError:
        subprocess.check_call(['useradd', '-ms', '/bin/bash', '-G', 'sudo', username])

c.Spawner.pre_spawn_hook = create_system_user
c.JupyterHub.template_paths = [f"{os.path.dirname(nativeauthenticator.__file__)}/templates/"]
c.NativeAuthenticator.open_signup = False
c.NativeAuthenticator.ask_email_on_signup = True
c.NativeAuthenticator.minimum_password_length = 8
c.NativeAuthenticator.allowed_failed_logins = 3
c.NativeAuthenticator.seconds_before_next_try = 600

# Allowed admins
admin = os.environ.get("JUPYTERHUB_ADMIN")
if admin:
    c.Authenticator.admin_users = {admin}
    c.JupyterHub.admin_access = True
