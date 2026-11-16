"""Tests for persistent local TCP port forwarding configuration."""

import json

import pytest

from devnaro import port_forwarding as forwarding


def test_add_and_load_forward(tmp_path):
    config = tmp_path / "port-forwards.json"
    forwarding.add_forward(5432, "warranty-manager-db", 5432, config)
    assert forwarding.load_forwards(config) == [
        forwarding.PortForward(5432, "warranty-manager-db", 5432)
    ]


def test_remove_forward(tmp_path):
    config = tmp_path / "port-forwards.json"
    forwarding.add_forward(5432, "db", 5432, config)
    assert forwarding.remove_forward(5432, config) is True
    assert forwarding.load_forwards(config) == []
    assert forwarding.remove_forward(5432, config) is False


def test_duplicate_local_port_is_rejected(tmp_path):
    config = tmp_path / "port-forwards.json"
    forwarding.add_forward(5432, "db", 5432, config)
    with pytest.raises(ValueError, match="already configured"):
        forwarding.add_forward(5432, "another-db", 5432, config)


@pytest.mark.parametrize("port", [0, 65536, -1, True])
def test_invalid_port_is_rejected(port):
    with pytest.raises(ValueError):
        forwarding.validate_port(port)


def test_invalid_target_host_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="Target must"):
        forwarding.add_forward(5432, "db;touch /tmp/pwned", 5432, tmp_path / "config")


def test_invalid_json_shape_is_rejected(tmp_path):
    config = tmp_path / "config"
    config.write_text(json.dumps({"local_port": 5432}), encoding="utf-8")
    with pytest.raises(ValueError, match="JSON array"):
        forwarding.load_forwards(config)
