import json
import os
import time
from pathlib import Path

import docker
from docker.errors import APIError, NotFound

# ==========================================
# Docker configuration
# ==========================================

client = docker.from_env()

DEVBOX_CONTAINER = os.getenv("HOSTNAME", "")

SYNC_INTERVAL = int(os.getenv("NETWORK_SYNC_INTERVAL", "10"))

EXCLUDE = {
    name.strip()
    for name in os.getenv("NETWORK_EXCLUDE", "bridge,host,none").split(",")
    if name.strip()
}

COMPOSE_ONLY = os.getenv("NETWORK_COMPOSE_ONLY", "true").lower() == "true"

EXCLUDE_INTERNAL = os.getenv("NETWORK_EXCLUDE_INTERNAL", "true").lower() == "true"


# ==========================================
# State persistence
# ==========================================

STATE_DIR = Path(
    os.getenv(
        "NETWORK_MANAGER_STATE_DIR", str(Path.home() / ".local/state/devbox-network-manager")
    )
)

STATE_FILE = STATE_DIR / "managed-networks.json"


def load_state():
    try:
        if not STATE_FILE.exists():
            return {}

        with STATE_FILE.open("r", encoding="utf-8") as file:
            state = json.load(file)

        if not isinstance(state, dict):
            raise ValueError("Invalid state format")

        return state

    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"[!] Could not load network state: {error}", flush=True)
        return {}


def save_state(state):
    try:
        STATE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
        STATE_DIR.chmod(0o700)

        temporary_file = STATE_FILE.with_suffix(".tmp")

        with temporary_file.open("w", encoding="utf-8") as file:
            json.dump(state, file, indent=2)

        temporary_file.chmod(0o600)
        temporary_file.replace(STATE_FILE)

    except OSError as error:
        print(f"[!] Could not save network state: {error}", flush=True)


# ==========================================
# Network eligibility
# ==========================================


def eligible(network):
    attrs = network.attrs

    name = network.name
    labels = attrs.get("Labels") or {}
    config = attrs.get("IPAM", {}).get("Config") or []

    if name in EXCLUDE:
        return False

    if attrs.get("Driver") != "bridge":
        return False

    if EXCLUDE_INTERNAL and attrs.get("Internal"):
        return False

    if COMPOSE_ONLY:
        if not labels.get("com.docker.compose.project"):
            return False

    if not config:
        return False

    return True


# ==========================================
# Network synchronization
# ==========================================


def synchronize():
    try:
        container = client.containers.get(DEVBOX_CONTAINER)
        container.reload()

        current = container.attrs.get("NetworkSettings", {}).get("Networks", {})

        state = load_state()

        desired = {}

        # Discover eligible Docker networks.
        for network in client.networks.list():
            try:
                network.reload()

                if eligible(network):
                    desired[network.name] = network.id

            except NotFound:
                continue

        # Connect eligible networks.
        for name, network_id in desired.items():

            if name in current:
                continue

            try:
                network = client.networks.get(network_id)
                network.connect(container)

                state[name] = network_id
                current[name] = {}

                print(f"[+] Connected: {name}", flush=True)

            except NotFound:
                continue

            except APIError as error:
                print(f"[!] Connect failed {name}: {error}", flush=True)

        # Disconnect only networks managed by this manager.
        for name, network_id in list(state.items()):

            if name not in current:
                state.pop(name, None)
                continue

            try:
                network = client.networks.get(network_id)
                network.reload()

                # Protect against a network being recreated
                # with the same name but a different ID.
                if network.id != network_id:
                    state.pop(name, None)
                    continue

                if eligible(network):
                    continue

                network.disconnect(container)

                state.pop(name, None)

                print(f"[-] Disconnected: {name}", flush=True)

            except NotFound:
                state.pop(name, None)

            except APIError as error:
                print(f"[!] Disconnect failed {name}: {error}", flush=True)

        save_state(state)

    except NotFound:
        print("[!] DevBox container not found", flush=True)

    except APIError as error:
        print(f"[!] Docker API error: {error}", flush=True)


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    print("[*] Network Manager started", flush=True)

    print(f"[*] Sync interval: {SYNC_INTERVAL}s", flush=True)

    print(f"[*] Compose-only mode: {COMPOSE_ONLY}", flush=True)

    while True:
        synchronize()
        time.sleep(SYNC_INTERVAL)
