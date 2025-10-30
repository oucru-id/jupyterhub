# JupyterHub configuration for single-container, multi-user setup

c = get_config()

# Configure custom templates directory
c.JupyterHub.template_paths = ['/srv/jupyterhub/templates']

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
            ], check=True)
            
            # Remove password expiry if it was set
            subprocess.run([
                'chage', '-d', '-1', username
            ], check=True)
            
            self.set_header('Content-Type', 'application/json')
            self.write({'status': 'success', 'message': 'Password changed successfully'})
        except subprocess.CalledProcessError as e:
            self.set_status(500)
            self.set_header('Content-Type', 'application/json')
            self.write({'status': 'error', 'message': f'Failed to change password: {e}'})
        except Exception as e:
            self.set_status(400)
            self.set_header('Content-Type', 'application/json')
            self.write({'status': 'error', 'message': str(e)})

class ChangePasswordPageHandler(BaseHandler):
    """Handler to serve the password change page"""
    
    async def get(self):
        """Serve the password change HTML page"""
        # Check if user is authenticated
        current_user = self.current_user
        if not current_user:
            raise web.HTTPError(401, "Authentication required")
            
        with open('/srv/jupyterhub/templates/change_password.html', 'r') as f:
            html_content = f.read()
        self.write(html_content)
        self.set_header('Content-Type', 'text/html')

# Use our custom authenticator
c.JupyterHub.authenticator_class = CustomPAMAuthenticator

# Register custom handlers
c.JupyterHub.extra_handlers = [
    (r'/api/set-password', SetPasswordHandler),
    (r'/set-password', SetPasswordPageHandler),
    (r'/api/change-password', ChangePasswordHandler),
    (r'/change-password', ChangePasswordPageHandler),
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

# Idle server culling configuration
# Cull idle servers after 30 minutes of inactivity
c.JupyterHub.services = [
    {
        'name': 'idle-culler',
        'command': [
            'python3', '-m', 'jupyterhub_idle_culler',
            '--timeout=1800',  # 30 minutes in seconds
            '--cull-every=300',  # Check every 5 minutes
            '--max-age=7200',  # Maximum server age: 2 hours
            '--remove-named-servers',  # Also remove named servers
        ],
        'admin': True,  # Give the service admin privileges
    }
]

# Alternative: Simple idle timeout (uncomment to use instead of idle-culler service)
# c.Spawner.http_timeout = 1800  # 30 minutes
# c.Spawner.start_timeout = 300  # 5 minutes to start
