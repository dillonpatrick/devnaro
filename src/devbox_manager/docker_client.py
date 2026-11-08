"""Docker client helpers."""

import docker
from docker.models.containers import Container


def get_client() -> docker.DockerClient:
    """Create a Docker client using the environment configuration."""
    return docker.from_env()


def get_devbox_container(client: docker.DockerClient) -> Container:
    """Return the configured DevBox container."""
    from devbox_manager.config import DEVBOX_CONTAINER

    return client.containers.get(DEVBOX_CONTAINER)
