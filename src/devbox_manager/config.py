"""Central configuration for the DevBox CLI."""

import os
from pathlib import Path

DEVBOX_CONTAINER = os.getenv("DEVBOX_CONTAINER", "devbox")
WORKSPACE_PATH = Path(os.getenv("WORKSPACE_PATH", "/workspace"))
NETWORK_MANAGER_LOG = Path(
    os.getenv("NETWORK_MANAGER_LOG", "/tmp/network-manager.log")
)
NETWORK_MANAGER_PROCESS = "/opt/network-manager/manager.py"
