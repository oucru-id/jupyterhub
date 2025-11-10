# JupyterHub on Docker

This repository contains a customized setup for running JupyterHub with Docker, designed for a multi-user environment where users are managed within the container.

## Features

- **JupyterHub with `LocalProcessSpawner`**: Spawns user notebooks as local processes within the JupyterHub container.
- **`NativeAuthenticator`**: Manages users directly within JupyterHub, allowing for self-registration and administrative control.
- **Dynamic User Creation**: A `pre_spawn_hook` automatically creates system users within the container when a new user signs up and is authorized.
- **Passwordless `sudo`**: Newly created users are added to the `sudo` group and are granted passwordless `sudo` privileges for seamless package installation and system management within their environment.
- **Idle Culler**: Includes a service to automatically stop inactive user servers to conserve resources.

## How It Works

1.  **Authentication**: `NativeAuthenticator` handles user login and registration. New users can sign up, but an admin must authorize them before they can log in.
2.  **User Creation**: When an authorized user logs in for the first time, the `pre_spawn_hook` in `jupyterhub_config.py` is triggered. This hook:
    - Checks if a system user with the same username exists.
    - If not, it creates a new system user and their home directory.
    - Adds the new user to the `sudo` group.
3.  **Spawning**: `LocalProcessSpawner` then starts the user's notebook server as a process running under their newly created system user account.
4.  **Sudo Access**: The `sudoconfig` file is copied into `/etc/sudoers.d/`, granting all users in the `sudo` group passwordless `sudo` access.

## Usage

1.  **Prerequisites**:
    - Install Docker and Docker Compose.

2.  **Build and Run**:
    ```bash
    docker-compose up --build -d
    ```

3.  **Access JupyterHub**:
    - Open your browser and navigate to `http://localhost:8000`.
    - The first user to sign up will be granted admin privileges.

## Configuration Files

- **`docker-compose.yml`**: Defines the JupyterHub service and mounts the necessary configurations. The container is run as `user: root` to allow for system user creation.
- **`Dockerfile`**: Builds the JupyterHub image, installing JupyterHub, `NativeAuthenticator`, and `sudo`. It also copies the `sudoconfig` file.
- **`jupyterhub_config.py`**: The main configuration file for JupyterHub. It sets up the authenticator, spawner, and the `pre_spawn_hook`.
- **`sudoconfig`**: A configuration file that grants passwordless `sudo` to the `sudo` group.