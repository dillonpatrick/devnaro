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



def test_format_ports_groups_consecutive_ranges():
    publishers = [
        {
            "URL": "127.0.0.1",
            "PublishedPort": port,
            "TargetPort": port,
            "Protocol": "tcp",
        }
        for port in [3000, 3001, 3002, 4173, 5000, 5001]
    ]

    assert status.format_ports(publishers) == [
        "127.0.0.1:3000-3002->3000-3002/tcp",
        "127.0.0.1:4173->4173/tcp",
        "127.0.0.1:5000-5001->5000-5001/tcp",
    ]


def test_format_created_prefers_relative_running_for():
    container = {
        "RunningFor": "About a minute",
        "CreatedAt": "2026-11-11 20:27:09 +0000 GMT",
    }

    assert status.format_created(container) == "About a minute"


def test_format_created_converts_absolute_timestamp_to_relative_age():
    created = {
        "CreatedAt": "2020-01-01 00:00:00 +0000 GMT",
    }

    result = status.format_created(created)

    assert result.endswith("ago")
    assert "2020-01-01" not in result



def test_render_uses_standard_panel_and_compact_ports():
    container = {
        "Name": "devbox",
        "Service": "devbox",
        "Image": "devbox-devbox",
        "Status": "Up 10 seconds",
        "RunningFor": "10 seconds",
        "Publishers": [
            {
                "URL": "127.0.0.1",
                "PublishedPort": port,
                "TargetPort": port,
                "Protocol": "tcp",
            }
            for port in [3000, 3001, 3002, 4173]
        ],
    }

    output = status.render([container], color=False, width=90)

    assert output.startswith("╭")
    assert "DevBox status" in output
    assert "│ DEVBOX" in output
    assert "127.0.0.1:3000-3002->3000-3002/tcp" in output
    assert "127.0.0.1:4173->4173/tcp" in output
    assert output.endswith("╯")
    assert "\\\\n" not in output
