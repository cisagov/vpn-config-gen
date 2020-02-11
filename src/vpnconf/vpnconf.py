#!/usr/bin/env python

"""Update the routes of an OpenVPN configuration.

Usage:
  vpnconf [--log-level=LEVEL] [--in-place] <filename>
  vpnconf (-h | --help)

Options:
  -h --help              Show this message.
  -i --in-place          Update file in place.
  --log-level=LEVEL      If specified, then the log level will be set to
                         the specified value.  Valid values are "debug", "info",
                         "warning", "error", and "critical". [default: warning]
"""

# Standard Python Libraries
import logging
import sys
import uuid

# Third-Party Libraries
import docopt
import netaddr
import requests
from tqdm import tqdm

from ._version import __version__

INSTANCE = "Worldwide"
STATIC_ROUTES = [netaddr.IPNetwork("172.20.0.0/24")]  # CAL


def make_json_request(url):
    """Make a json request and handle status codes."""
    r = requests.get(url)
    if r.status_code != 200:
        raise Exception(f"Bad request status_code: {r.status_code}")
    return r.json()


def get_latest_versions(guid, instance_name):
    """Get the latest versions of each service instance."""
    json = make_json_request(
        f"https://endpoints.office.com/version?clientrequestid={guid}"
    )
    for d in json:
        if d["instance"] == instance_name:
            return d["latest"]
    else:
        return None


def get_endpoints(guid, instance_name):
    """Gather endpoints from office API."""
    ip_set = netaddr.IPSet()
    tqdm.write(f"requesting endpoints for: {instance_name}")
    json = make_json_request(
        f"https://endpoints.office.com/endpoints/{instance_name}?clientrequestid={guid}"
    )
    for service in tqdm(json, desc="Gathering", unit="services", leave=True):
        for ip in service.get("ips", []):
            ip_set.add(ip)
    ip_set.compact()
    return ip_set


def generate_routes(ip_set, v4_only=False):
    """Generate route lines for vpn configuration."""
    lines = []
    for ip in ip_set.iter_cidrs():
        if ip.version == 4:
            # route network netmask gateway metric
            lines.append(f"route {ip.network} {ip.netmask} vpn_gateway default")
        elif ip.version == 6 and not v4_only:
            # route network/bits gateway metric
            lines.append(f"route-ipv6 {ip} default default")
    return lines


def read_config_no_routes(filename):
    """Read a VPN configuration and strip out route lines."""
    lines = []
    if filename == "-":
        f = sys.stdin
    else:
        f = open(filename, "r")
    for line in f.readlines():
        if line.startswith("route ") or line.startswith("route-ipv6 "):
            continue
        lines.append(line.strip())
    if f is not sys.stdin:
        f.close()
    return lines


def write_config(lines, filename):
    """Write the configuration to disk."""
    with open(filename, "w") as f:
        for line in lines:
            print(line, file=f)


def main():
    """Set up logging and call the vpnconf function."""
    args = docopt.docopt(__doc__, version=__version__)
    # Set up logging
    log_level = args["--log-level"]
    try:
        logging.basicConfig(
            format="%(asctime)-15s %(levelname)s %(message)s", level=log_level.upper()
        )
    except ValueError:
        logging.critical(
            f'"{log_level}" is not a valid logging level.  Possible values '
            "are debug, info, warning, and error."
        )
        return 1

    lines = read_config_no_routes(args["<filename>"])

    guid = uuid.uuid1()
    # version = get_latest_versions(guid, INSTANCE)
    ip_set = get_endpoints(guid, INSTANCE)

    # add our static routes
    ip_set = ip_set.union(STATIC_ROUTES)
    lines += generate_routes(ip_set)

    if args["--in-place"]:
        write_config(lines, args["<filename>"])
    else:
        for line in lines:
            print(line)

    # Stop logging and clean up
    logging.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
