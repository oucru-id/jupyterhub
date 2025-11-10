# JupyterHub on Docker

This repository contains a basic setup for running JupyterHub with Docker.

## Features

- JupyterHub with DockerSpawner
- Native Authenticator for user management
- Idle culler to stop inactive servers

## Usage

1.  Install Docker and Docker Compose.
2.  Run `docker-compose up -d`.
3.  Access JupyterHub at `http://localhost:8000`.