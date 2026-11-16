"""Central configuration for the DevNaro CLI."""

import os
from pathlib import Path

DEVNARO_CONTAINER = os.getenv("DEVNARO_CONTAINER", "devnaro")
WORKSPACE_PATH = Path(os.getenv("WORKSPACE_PATH", "/workspace"))
NETWORK_MANAGER_LOG = Path(
    os.getenv("NETWORK_MANAGER_LOG", "/tmp/network-manager.log")
)
NETWORK_MANAGER_PROCESS = "/opt/network-manager/manager.py"
