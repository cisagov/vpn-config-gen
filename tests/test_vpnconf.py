#!/usr/bin/env pytest -vs
"""Tests for vpnconf."""

# Standard Python Libraries
import logging
import os
import sys
from unittest.mock import patch

# Third-Party Libraries
import netaddr
import pytest

# cisagov Libraries
import vpnconf
from vpnconf import vpnconf as vpnconf_module  # Import the module
from vpnconf.vpnconf import (  # Import the functions
    generate_routes,
    get_endpoints,
    make_json_request,
    parse_extra_routes,
    read_config_no_routes,
    write_config,
)

log_levels = (
    "debug",
    "info",
    "warning",
    "error",
    "critical",
)

# define sources of version strings
RELEASE_TAG = os.getenv("RELEASE_TAG")
PROJECT_VERSION = vpnconf_module.__version__


def test_stdout_version(capsys):
    """Verify that version string sent to stdout agrees with the module version."""
    with pytest.raises(SystemExit):
        with patch.object(sys, "argv", ["bogus", "--version"]):
            vpnconf_module.main()
    captured = capsys.readouterr()
    assert (
        captured.out == f"{PROJECT_VERSION}\n"
    ), "standard output by '--version' should agree with module.__version__"


def test_running_as_module(capsys):
    """Verify that the __main__.py file loads correctly."""
    with pytest.raises(SystemExit):
        with patch.object(sys, "argv", ["bogus", "--version"]):
            # F401 is a "Module imported but unused" warning. This import
            # emulates how this project would be run as a module. The only thing
            # being done by __main__ is importing the main entrypoint of the
            # package and running it, so there is nothing to use from this
            # import. As a result, we can safely ignore this warning.
            # cisagov Libraries
            import vpnconf.__main__  # noqa: F401
    captured = capsys.readouterr()
    assert (
        captured.out == f"{PROJECT_VERSION}\n"
    ), "standard output by '--version' should agree with module.__version__"


@pytest.mark.skipif(
    RELEASE_TAG in [None, ""], reason="this is not a release (RELEASE_TAG not set)"
)
def test_release_version():
    """Verify that release tag version agrees with the module version."""
    assert (
        RELEASE_TAG == f"v{PROJECT_VERSION}"
    ), "RELEASE_TAG does not match the project version"


@pytest.mark.parametrize("level", log_levels)
def test_log_levels(level):
    """Validate commandline log-level arguments."""
    with patch.object(
        sys, "argv", ["bogus", f"--log-level={level}", "tests/sample.conf"]
    ):
        with patch.object(logging.root, "handlers", []):
            assert (
                logging.root.hasHandlers() is False
            ), "root logger should not have handlers yet"
            return_code = None
            try:
                vpnconf.vpnconf.main()
            except SystemExit as sys_exit:
                return_code = sys_exit.code
            assert return_code is None, "main() should return success"
            assert (
                logging.root.hasHandlers() is True
            ), "root logger should now have a handler"
            assert (
                logging.getLevelName(logging.root.getEffectiveLevel()) == level.upper()
            ), f"root logger level should be set to {level.upper()}"
            assert return_code is None, "main() should return success"


def test_bad_log_level():
    """Validate bad log-level argument returns error."""
    with patch.object(
        sys, "argv", ["bogus", "--log-level=emergency", "tests/sample.conf"]
    ):
        return_code = None
        try:
            vpnconf.vpnconf.main()
        except SystemExit as sys_exit:
            return_code = sys_exit.code
        assert return_code == 1, "main() should exit with error"


def test_make_json_request(mocker):
    """Test the make_json_request function with a mocked GET request."""
    mocker.patch(
        "requests.get",
        return_value=mocker.MagicMock(status_code=200, json=lambda: {"test": "data"}),
    )
    assert make_json_request("test_url") == {"test": "data"}


def test_get_endpoints(mocker):
    """Test the get_endpoints function to ensure it returns the correct IPSet."""
    mock_json_request = [
        {"ips": ["192.0.2.0/24", "2001:db8::/32"]},
        {"ips": ["198.51.100.0/24", "2001:db8:0:1::/64"]},
    ]
    mocker.patch("vpnconf.vpnconf.make_json_request", return_value=mock_json_request)
    ip_set = get_endpoints("1234", "test_instance")
    assert isinstance(ip_set, netaddr.IPSet)
    assert netaddr.IPNetwork("192.0.2.0/24") in ip_set
    assert netaddr.IPNetwork("198.51.100.0/24") in ip_set
    assert netaddr.IPNetwork("2001:db8::/32") in ip_set
    assert netaddr.IPNetwork("2001:db8:0:1::/64") in ip_set


def test_generate_routes():
    """Test the generate_routes function to ensure it produces the correct routing lines."""
    ip_set = netaddr.IPSet(
        ["192.0.2.0/24", "198.51.100.0/24", "2001:db8::/32", "2001:db8:0:1::/64"]
    )
    lines = generate_routes(ip_set)
    expected_lines = [
        "route 192.0.2.0 255.255.255.0 vpn_gateway default",
        "route 198.51.100.0 255.255.255.0 vpn_gateway default",
        "route-ipv6 2001:db8::/32 default default",
    ]
    assert lines == expected_lines


def test_read_config_no_routes(tmp_path):
    """Test the read_config_no_routes function to ensure it removes route lines."""
    file_path = tmp_path / "test.conf"
    content = "\n".join(
        [
            "client",
            "dev tun",
            "proto udp",
            "remote vpn.example.com 1194",
            "route 192.0.2.0 255.255.255.0 vpn_gateway default",
            "route-ipv6 2001:db8::/32 default default",
            "<ca>",
            "...",
            "</ca>",
        ]
    )
    file_path.write_text(content)
    lines = read_config_no_routes(file_path)
    expected_lines = [
        "client",
        "dev tun",
        "proto udp",
        "remote vpn.example.com 1194",
        "<ca>",
        "...",
        "</ca>",
    ]
    assert lines == expected_lines


def test_write_config(tmp_path):
    """Test the write_config function."""
    lines = [
        "client",
        "dev tun",
        "proto udp",
        "remote vpn.example.com 1194",
        "<ca>",
        "...",
        "</ca>",
    ]
    file_path = tmp_path / "test.conf"
    write_config(lines, file_path)
    content = file_path.read_text()
    assert content == "\n".join(lines) + "\n"


def test_parse_extra_routes(mocker, tmp_path):
    """Test the parse_extra_routes function with mock DNS resolution and temporary files."""
    # File with hostnames and IP networks
    file1 = tmp_path / "extra_routes1.txt"
    file1.write_text(
        "\n".join(["example.com", "www.example.com", "192.0.2.0/24", "2001:db8::/32"])
    )
    # File with only an IP network
    file2 = tmp_path / "extra_routes2.txt"
    file2.write_text("198.51.100.0/24")
    # Mock DNS resolver to return IP addresses for hostnames
    dns_resolve_mock = mocker.patch("dns.resolver.resolve")
    dns_resolve_mock.side_effect = [
        [
            mocker.MagicMock(address="93.184.216.34"),
            mocker.MagicMock(address="2606:2800:220:1:248:1893:25c8:1946"),
        ],  # example.com
        [
            mocker.MagicMock(address="93.184.216.34"),
            mocker.MagicMock(address="2606:2800:220:1:248:1893:25c8:1946"),
        ],  # www.example.com
    ]
    ip_set, dns_errors = parse_extra_routes([file1, file2])
    assert isinstance(ip_set, netaddr.IPSet)
    assert netaddr.IPNetwork("192.0.2.0/24") in ip_set
    assert netaddr.IPNetwork("198.51.100.0/24") in ip_set
    assert netaddr.IPNetwork("2001:db8::/32") in ip_set
    assert netaddr.IPNetwork("93.184.216.34") in ip_set
    assert netaddr.IPNetwork("2606:2800:220:1:248:1893:25c8:1946") in ip_set
    assert dns_errors == set()
