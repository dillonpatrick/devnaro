#!/usr/bin/env python3
"""Host-side Unix socket bridge that opens DevBox paths in the host VS Code."""

import argparse
import json
import os
import shutil
import socketserver
import subprocess
import threading
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

            vscode = shutil.which("code")
            if not vscode:
                raise RuntimeError(
                    "VS Code CLI 'code' was not found on the host PATH. "
                    "Install VS Code and make its 'code' command available."
                )

            subprocess.Popen(
                [vscode, "--reuse-window", str(target)],
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
