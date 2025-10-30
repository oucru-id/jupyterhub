# JupyterHub configuration for single-container, multi-user setup

c = get_config()

# Custom authenticator that can create users
import subprocess
import os
from jupyterhub.auth import PAMAuthenticator
from jupyterhub.handlers import BaseHandler
from tornado import web
import json

class CustomPAMAuthenticator(PAMAuthenticator):
    async def add_user(self, user):
        """Add a new user by creating a system user"""
        username = user.name
        try:
            # Create system user with home directory
            subprocess.run([
                'useradd', '-m', '-s', '/bin/bash', username
            ], check=True)
            
            # Set a default password that user should change on first login
            # You can change this default password here
            default_password = "ChangeMe123!"
            subprocess.run([
                'bash', '-c', f'echo "{username}:{default_password}" | chpasswd'
            ], check=True)
            
            # Force password change on first login
            subprocess.run([
                'chage', '-d', '0', username
            ], check=True)
            
            print(f"Created system user: {username} with default password: {default_password}")
            print(f"User will be required to change password on first login")
        except subprocess.CalledProcessError as e:
            print(f"Failed to create user {username}: {e}")
            raise
        
        # Call parent method to add to JupyterHub
        return await super().add_user(user)

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
            ], check=True)
            
            # Remove password expiry if it was set
            subprocess.run([
                'chage', '-d', '-1', username
            ], check=True)
            
            self.set_header('Content-Type', 'application/json')
            self.write({'status': 'success', 'message': f'Password set for user {username}'})
        except subprocess.CalledProcessError as e:
            self.set_status(500)
            self.set_header('Content-Type', 'application/json')
            self.write({'status': 'error', 'message': f'Failed to set password: {e}'})
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
            
        with open('/srv/jupyterhub/templates/set_password.html', 'r') as f:
            html_content = f.read()
        self.write(html_content)
        self.set_header('Content-Type', 'text/html')

# Use our custom authenticator
c.JupyterHub.authenticator_class = CustomPAMAuthenticator

# Register custom handlers
c.JupyterHub.extra_handlers = [
    (r'/api/set-password', SetPasswordHandler),
    (r'/set-password', SetPasswordPageHandler),
]

# Each user spawns a local JupyterLab process inside this same container
c.JupyterHub.spawner_class = 'jupyterhub.spawner.LocalProcessSpawner'

# Configure the spawner to use the correct Jupyter executable
c.Spawner.cmd = ['jupyter-labhub']
c.Spawner.args = ['--allow-root']

# Default landing page
c.Spawner.default_url = '/lab'

# Allow any valid system user to login (no need to manually add each user)
c.Authenticator.allow_all = True

# Optional admin user (root)
c.Authenticator.admin_users = {'root'}

# Notebooks stored in each user's home directory
# Use template string that JupyterHub will expand
c.Spawner.notebook_dir = '~'

# Set the working directory for spawned processes to user's home
c.Spawner.cwd = '~'

# Run on all interfaces, default port 8000
c.JupyterHub.bind_url = 'http://:8000'

# Database and cookie files (local SQLite)
c.JupyterHub.cookie_secret_file = '/srv/jupyterhub/jupyterhub_cookie_secret'
c.JupyterHub.db_url = 'sqlite:////srv/jupyterhub/jupyterhub.sqlite'

# Increase timeout for spawner startup
c.Spawner.start_timeout = 60

# Environment variables for spawned servers
c.Spawner.environment = {
    'JUPYTERHUB_SINGLEUSER_APP': 'jupyter_server.serverapp.ServerApp',
}
