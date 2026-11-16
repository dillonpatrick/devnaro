"""Docker client helpers."""

import docker
from docker.models.containers import Container


def get_client() -> docker.DockerClient:
    """Create a Docker client using the environment configuration."""
    return docker.from_env()


def get_devnaro_container(client: docker.DockerClient) -> Container:
    """Return the configured DevNaro container."""
    from devnaro.config import DEVNARO_CONTAINER

    return client.containers.get(DEVNARO_CONTAINER)
