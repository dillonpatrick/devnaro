#!/usr/bin/env python3
"""Host-side bridge that opens DevBox paths in VS Code with a DevBox terminal profile."""

import argparse
import hashlib
import json
import os
import shutil
import socketserver
import subprocess
from pathlib import Path


class BridgeHandler(socketserver.StreamRequestHandler):
    def handle(self):
        try:
            request = json.loads(self.rfile.readline())
            container_path = Path(request["path"])
            workspace = Path(self.server.workspace).resolve()

            if not container_path.is_absolute() or not (
                container_path == Path("/workspace")
                or Path("/workspace") in container_path.parents
            ):
                raise ValueError("Only paths inside /workspace can be opened.")

            relative_path = container_path.relative_to("/workspace")
            target = (workspace / relative_path).resolve()

            if target != workspace and workspace not in target.parents:
                raise ValueError("The requested path resolves outside the workspace.")
            if not target.exists():
                raise ValueError(f"Path does not exist: {container_path}")

            # VS Code workspace folders must be directories. For a file request,
            # open its containing project directory.
            folder = target if target.is_dir() else target.parent
            container_folder = Path("/workspace") / folder.relative_to(workspace)

            vscode = shutil.which("code")
            if not vscode:
                raise RuntimeError(
                    "VS Code CLI 'code' was not found on the host PATH. "
                    "Install VS Code and make its 'code' command available."
                )

            bridge_script = Path(__file__).with_name("vscode-terminal.sh").resolve()
            if not bridge_script.is_file():
                raise RuntimeError(f"VS Code terminal launcher not found: {bridge_script}")

            cache_root = Path(
                os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))
            ) / "devbox" / "vscode-workspaces"
            cache_root.mkdir(parents=True, exist_ok=True)

            workspace_id = hashlib.sha256(str(folder).encode()).hexdigest()[:16]
            workspace_file = cache_root / f"{workspace_id}.code-workspace"
            workspace_config = {
                "folders": [{"path": str(folder)}],
                "settings": {
                    "terminal.integrated.profiles.linux": {
                        "DevBox": {
                            "path": "/bin/bash",
                            "args": [str(bridge_script), str(container_folder)],
                            "icon": "terminal-linux",
                        }
                    },
                    "terminal.integrated.defaultProfile.linux": "DevBox",
                },
            }
            workspace_file.write_text(
                json.dumps(workspace_config, indent=2) + "\n",
                encoding="utf-8",
            )

            subprocess.Popen(
                [vscode, "--reuse-window", str(workspace_file)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            response = {"ok": True}
        except Exception as exc:  # Return actionable errors to the container CLI.
            response = {"ok": False, "error": str(exc)}

        self.wfile.write((json.dumps(response) + "\n").encode())


class ThreadedUnixServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", required=True)
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()

    socket_path = Path(args.socket)
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    if socket_path.exists():
        socket_path.unlink()

    server = ThreadedUnixServer(str(socket_path), BridgeHandler)
    server.workspace = str(Path(args.workspace).resolve())
    os.chmod(socket_path, 0o600)

    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        server.server_close()
        socket_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
