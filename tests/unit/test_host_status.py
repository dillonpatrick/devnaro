import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).parents[2] / "scripts" / "host" / "status.py"
SPEC = importlib.util.spec_from_file_location("devbox_host_status", MODULE_PATH)
assert SPEC and SPEC.loader
status = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(status)


def test_load_containers_accepts_compose_json_array():
    containers = status.load_containers(
        '[{"Name":"devbox","Status":"Up 10 seconds"}]'
    )

    assert len(containers) == 1
    assert containers[0]["Name"] == "devbox"


def test_render_shows_container_details_and_published_ports():
    containers = [
        {
            "Name": "devbox",
            "Service": "devbox",
            "Image": "devbox-devbox:latest",
            "Status": "Up 45 seconds",
            "CreatedAt": "45 seconds ago",
            "Publishers": [
                {
                    "URL": "127.0.0.1",
                    "PublishedPort": 3000,
                    "TargetPort": 3000,
                    "Protocol": "tcp",
                },
                {
                    "URL": "127.0.0.1",
                    "PublishedPort": 4173,
                    "TargetPort": 4173,
                    "Protocol": "tcp",
                },
            ],
        }
    ]

    output = status.render(containers, color=False)

    assert "DEVBOX  devbox" in output
    assert "Image" in output
    assert "Up 45 seconds" in output
    assert "127.0.0.1:3000->3000/tcp" in output
    assert "127.0.0.1:4173->4173/tcp" in output


def test_render_handles_missing_container():
    output = status.render([], color=False)

    assert "No container found" in output
    assert "devbox start" in output


def test_status_style_distinguishes_container_states():
    assert status.status_style("Up 10 seconds") == status.GREEN
    assert status.status_style("Exited (1)") == status.RED
    assert status.status_style("Created") == status.YELLOW
