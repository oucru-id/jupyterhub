# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

# Configuration file for JupyterHub
import os

c = get_config()  # noqa: F821

# We rely on environment variables to configure JupyterHub so that we
# avoid having to rebuild the JupyterHub container every time we change a
# configuration parameter.

# Redirect users to hub home instead of auto-spawning servers
c.JupyterHub.redirect_to_server = False

# Spawn single-user servers as Docker containers
c.JupyterHub.spawner_class = "dockerspawner.DockerSpawner"

# Spawn containers from this image
c.DockerSpawner.image = os.environ["DOCKER_NOTEBOOK_IMAGE"]

# Connect containers to this Docker network
network_name = os.environ["DOCKER_NETWORK_NAME"]
c.DockerSpawner.use_internal_ip = True
c.DockerSpawner.network_name = network_name

# Explicitly set notebook directory because we'll be mounting a volume to it.
# Most `jupyter/docker-stacks` *-notebook images run the Notebook server as
# user `jovyan`, and set the notebook directory to `/home/jovyan/work`.
# We follow the same convention.
notebook_dir = os.environ.get("DOCKER_NOTEBOOK_DIR", "/home/jovyan/work")
c.DockerSpawner.notebook_dir = notebook_dir

# Mount the real user's Docker volume on the host to the notebook user's
# notebook directory in the container
c.DockerSpawner.volumes = {"jupyterhub-user-{username}": notebook_dir}

# Remove containers once they are stopped
c.DockerSpawner.remove = True

# For debugging arguments passed to spawned containers
c.DockerSpawner.debug = True

# User containers will access hub by container name on the Docker network
c.JupyterHub.hub_ip = "jupyterhub"
c.JupyterHub.hub_port = 8080

# Persist hub data on volume mounted inside container
c.JupyterHub.cookie_secret_file = "/data/jupyterhub_cookie_secret"
c.JupyterHub.db_url = "sqlite:////data/jupyterhub.sqlite"

# Allow all signed-up users to login
c.Authenticator.allow_all = True

# Authenticate users with PAM Authenticator
c.JupyterHub.authenticator_class = 'jupyterhub.auth.PAMAuthenticator'
c.Authenticator.create_system_users = True

# Allowed admins
admin = os.environ.get("JUPYTERHUB_ADMIN")
if admin:
    c.Authenticator.admin_users = [admin]

# ======================================================
# Custom handlers for setting and changing passwords
# ======================================================
import json
import subprocess
from tornado import web
from jupyterhub.handlers import BaseHandler

class SetPasswordHandler(BaseHandler):
    """Custom handler for setting user passwords"""
    
    async def post(self):
        """Set password for a user"""
        # Check if current user is admin
        current_user = self.current_user
        if not current_user or not current_user.admin:
            self.set_status(403)
            self.write({'status': 'error', 'message': 'Admin access required'})
            return
            
        try:
            data = json.loads(self.request.body.decode('utf-8'))
            username = data.get('username')
            password = data.get('password')
            
            if not username or not password:
                self.set_status(400)
                self.write({'status': 'error', 'message': 'Username and password required'})
                return
            
            # Set the password
            subprocess.run([
                'bash', '-c', f'echo "{username}:{password}" | chpasswd'
            ], check=True, capture_output=True, text=True)
            
            # Remove password expiry if it was set
            subprocess.run([
                'chage', '-d', '-1', username
            ], check=True, capture_output=True, text=True)
            
            self.set_header('Content-Type', 'application/json')
            self.write({'status': 'success', 'message': f'Password set for user {username}'})
        except subprocess.CalledProcessError as e:
            self.set_status(500)
            self.set_header('Content-Type', 'application/json')
            self.write({'status': 'error', 'message': f'Failed to set password: {e.stderr}'})
        except Exception as e:
            self.set_status(400)
            self.set_header('Content-Type', 'application/json')
            self.write({'status': 'error', 'message': str(e)})

class SetPasswordPageHandler(BaseHandler):
    """Handler to serve the password setting page"""
    
    async def get(self):
        """Serve the password setting HTML page"""
        # Check if current user is admin
        current_user = self.current_user
        if not current_user or not current_user.admin:
            raise web.HTTPError(403, "Admin access required")
            
        html = await self.render_template("set_password.html", xsrf_token=self.xsrf_token)
        self.finish(html)

class ChangePasswordPageHandler(BaseHandler):
    """Handler to serve the password change page"""
    
    async def get(self):
        """Serve the password change HTML page"""
        # Check if user is authenticated
        current_user = self.current_user
        if not current_user:
            raise web.HTTPError(401, "Authentication required")
            
        html = await self.render_template("change_password.html", xsrf_token=self.xsrf_token)
        self.finish(html)

class ChangePasswordHandler(BaseHandler):
    """Handler for users to change their own passwords"""
    
    async def post(self):
        """Change password for the current user"""
        # Check if user is authenticated
        current_user = self.current_user
        if not current_user:
            self.set_status(401)
            self.write({'status': 'error', 'message': 'Authentication required'})
            return
            
        try:
            data = json.loads(self.request.body.decode('utf-8'))
            current_password = data.get('current_password')
            new_password = data.get('new_password')
            
            if not current_password or not new_password:
                self.set_status(400)
                self.write({'status': 'error', 'message': 'Current password and new password required'})
                return
            
            username = current_user.name
            
            # Verify current password using PAM
            try:
                # Use subprocess to verify password with su command
                result = subprocess.run([
                    'su', '-c', 'echo "Password verified"', username
                ], input=current_password, text=True, capture_output=True, timeout=10)
                
                if result.returncode != 0:
                    self.set_status(400)
                    self.set_header('Content-Type', 'application/json')
                    self.write({'status': 'error', 'message': 'Current password is incorrect'})
                    return
            except subprocess.TimeoutExpired:
                self.set_status(400)
                self.set_header('Content-Type', 'application/json')
                self.write({'status': 'error', 'message': 'Password verification timeout'})
                return
            except Exception as verify_error:
                self.set_status(500)
                self.set_header('Content-Type', 'application/json')
                self.write({'status': 'error', 'message': f'Password verification failed: {verify_error}'})
                return
            
            # Set the new password
            subprocess.run([
                'bash', '-c', f'echo "{username}:{new_password}" | chpasswd'
            ], check=True, capture_output=True, text=True)
            
            # Remove password expiry if it was set
            subprocess.run([
                'chage', '-d', '-1', username
            ], check=True, capture_output=True, text=True)
            
            self.set_header('Content-Type', 'application/json')
            self.write({'status': 'success', 'message': 'Password changed successfully'})
        except subprocess.CalledProcessError as e:
            self.set_status(500)
            self.set_header('Content-Type', 'application/json')
            self.write({'status': 'error', 'message': f'Failed to change password: {e.stderr}'})
        except Exception as e:
            self.set_status(400)
            self.set_header('Content-Type', 'application/json')
            self.write({'status': 'error', 'message': str(e)})

# Register custom handlers
c.JupyterHub.extra_handlers = [
    (r'/api/set-password', SetPasswordHandler),
    (r'/set-password', SetPasswordPageHandler),
    (r'/change-password', ChangePasswordPageHandler),
    (r'/api/change-password', ChangePasswordHandler),
]

# Add templates path
c.JupyterHub.template_paths = ['/srv/jupyterhub/templates']
