"""Update the routes of an OpenVPN configuration.

There are certain internet services that filter access based on egress.
This tool will update the routes of an OpenVPN configuration file to include
the latest routes for those IP addresses.

Usage:
  vpnconf [--log-level=LEVEL] [--in-place] [--no-ipv4 | --no-ipv6] [-e FILES...] <filename>
  vpnconf (-h | --help)

Options:
  -h --help              Show this message.
  -e FILES --extra-routes=FILES   Additional files containing hostnames or CIDRs.
  -i --in-place          Update file in place.
  --no-ipv4              Exclude IPv4 addresses from the output.
  --no-ipv6              Exclude IPv6 addresses from the output.
  --log-level=LEVEL      If specified, then the log level will be set to
                         the specified value.  Valid values are "debug", "info",
                         "warning", "error", and "critical". [default: warning]
"""


# Standard Python Libraries
import logging
import sys
import uuid

# Third-Party Libraries
import dns.resolver
import docopt
import netaddr
import requests
from schema import And, Optional, Or, Schema, SchemaError, Use
from tqdm import tqdm

from ._version import __version__

INSTANCE = "Worldwide"


def make_json_request(url):
    """Make a JSON request and handle status codes.

    This function sends a GET request to the provided URL expecting a JSON response.

    Parameters:
    url (str): The URL to which the request is sent.

    Returns:
    dict: The JSON response converted to a dictionary.

    Raises:
    Exception: If the status code of the response is not 200.
    """
    r = requests.get(url)
    if r.status_code != 200:
        raise Exception(f"Bad request status_code: {r.status_code}")
    return r.json()


def get_endpoints(guid, instance_name):
    """Gather endpoints from Office API.

    This function collects endpoints for a specified instance from the Office API and returns them as an IP set.

    Parameters:
    guid (str): The globally unique identifier used for the client request.
    instance_name (str): The name of the instance for which endpoints are being gathered.

    Returns:
    netaddr.IPSet: A set of gathered IP networks.
    """
    ip_set = netaddr.IPSet()
    tqdm.write(f"Requesting endpoints for: {instance_name}")
    json = make_json_request(
        f"https://endpoints.office.com/endpoints/{instance_name}?clientrequestid={guid}"
    )
    for service in tqdm(json, desc="Gathering", unit="services", leave=True):
        # Add each IP to the set
        for ip in service.get("ips", []):
            ip_set.add(ip)
    ip_set.compact()
    return ip_set


def generate_routes(ip_set, no_ipv4=False, no_ipv6=False):
    """Generate route lines for VPN configuration.

    This function generates route lines based on the given IP set. It generates both IPv4 and IPv6 routes
    depending on the provided parameters.

    Parameters:
    ip_set (netaddr.IPSet): A set of resolved IP networks.
    no_ipv4 (bool): If True, do not generate IPv4 routes. Defaults to False.
    no_ipv6 (bool): If True, do not generate IPv6 routes. Defaults to False.

    Returns:
    lines (list): A list of generated route lines.
    """
    lines = []
    for ip in tqdm(ip_set.iter_cidrs(), desc="Generating", unit="routes", leave=True):
        if ip.version == 4 and not no_ipv4:
            # Generate an IPv4 route line
            lines.append(f"route {ip.network} {ip.netmask} vpn_gateway default")
        elif ip.version == 6 and not no_ipv6:
            # Generate an IPv6 route line
            lines.append(f"route-ipv6 {ip} default default")
    return lines


def read_config_no_routes(filename):
    """Read a VPN configuration and strip out route lines.

    This function reads a VPN configuration file and removes any existing route lines.

    Parameters:
    filename (str): Path of the VPN configuration file.

    Returns:
    lines (list): A list of configuration lines without any route lines.
    """
    lines = []
    if filename == "-":
        f = sys.stdin
    else:
        f = open(filename)
    for line in f.readlines():
        # Skip route lines
        if line.startswith("route ") or line.startswith("route-ipv6 "):
            continue
        lines.append(line.strip())
    if f is not sys.stdin:
        f.close()
    return lines


def write_config(lines, filename):
    """Write the configuration to disk.

    This function writes a list of configuration lines to a file.

    Parameters:
    lines (list): A list of configuration lines.
    filename (str): Path of the file where the configuration will be written.
    """
    with open(filename, "w") as f:
        for line in lines:
            print(line, file=f)


def parse_extra_routes(files):
    """Parse a list of files containing additional routes.

    This function reads each file line by line and tries to interpret each line as an IP network.
    If the line cannot be interpreted as an IP network, it treats the line as a hostname and tries to resolve it to an IPv4 or IPv6 address.
    If the hostname can't be resolved to either an IPv4 or IPv6 address, it logs a warning and adds the hostname to a set of failed DNS lookups.

    Parameters:
    files (list): A list of file paths to read for hostnames or IP networks.

    Returns:
    ip_set (netaddr.IPSet): A set of resolved IP networks.
    dns_errors (set): A set of hostnames that could not be resolved to an IP address.
    """
    ip_set = netaddr.IPSet()
    dns_errors = set()
    for file in tqdm(files, desc="Reading extra routes", unit="file", leave=True):
        logging.info(f"Reading extra routes from {file}")
        with open(file) as f:
            for line in f.readlines():
                if line.startswith("#"):
                    # Skip comment lines
                    continue
                line = line.strip()
                if line:
                    try:
                        # Try to interpret the line as an IP network
                        ip_set.add(netaddr.IPNetwork(line))
                    except netaddr.core.AddrFormatError:
                        # If the line is not a valid IP network, try to resolve it as a hostname
                        logging.debug(f"Resolving hostname: {line}")
                        resolved = False
                        for query_type in ("A", "AAAA"):
                            try:
                                # Attempt to resolve the hostname to an IP address
                                addresses = [
                                    str(rdata)
                                    for rdata in dns.resolver.resolve(line, query_type)
                                ]
                                for ip in addresses:
                                    ip_set.add(netaddr.IPNetwork(ip))
                                    resolved = True
                            except dns.resolver.NoAnswer:
                                # If no IP address was found for the hostname, log a debug message
                                logging.debug(
                                    f"No {query_type} answer for {line} in {file}"
                                )
                            except dns.resolver.NXDOMAIN:
                                # If the hostname does not exist, log a warning and add to error set
                                logging.warning(
                                    f"Could not resolve hostname {line} in {file}"
                                )
                                dns_errors.add(line)
                        if not resolved:
                            # If the hostname couldn't be resolved to an IPv4 or IPv6 address, log a warning
                            logging.warning(
                                f"Could not resolve {line} to either an IPv4 or IPv6 address."
                            )
    return ip_set, dns_errors


def main():
    """Parse command line arguments and run the program."""
    args = docopt.docopt(__doc__, version=__version__)

    # Define the validation schema for the input arguments
    schema = Schema(
        {
            "--log-level": And(
                str,
                Use(str.lower),
                lambda n: n in ("debug", "info", "warning", "error", "critical"),
                error="Possible values for --log-level are "
                + "debug, info, warning, error, and critical.",
            ),
            Optional(Or("-e", "--extra-routes")): list,
            "--no-ipv4": bool,
            "--no-ipv6": bool,
            str: object,  # Don't care about other keys, if any
        }
    )

    try:
        # Validate the input arguments against the schema
        args = schema.validate(args)
    except SchemaError as err:
        # If arguments validation fails, print the error and terminate the program
        print(err, file=sys.stderr)
        sys.exit(1)

    # Assign the validated arguments to corresponding variables
    filename = args["<filename>"]
    log_level = args["--log-level"]
    no_ipv4 = args["--no-ipv4"]
    no_ipv6 = args["--no-ipv6"]

    # Configure the logging system
    logging.basicConfig(
        format="%(asctime)-15s %(levelname)s %(message)s", level=log_level.upper()
    )

    # Read the configuration file and remove any existing route lines
    lines = read_config_no_routes(filename)

    # Generate a UUID and use it to get the IP endpoints for the specified instance
    guid = uuid.uuid1()
    ip_set = get_endpoints(guid, INSTANCE)

    # If extra routes files are provided, parse them and add their routes to the set
    extra_routes, dns_errors = parse_extra_routes(args["--extra-routes"])
    if dns_errors:
        # If there were unresolved hostnames, log an error and terminate the program
        logging.error(
            f"Could not resolve the following hostnames: {', '.join(dns_errors)}"
        )
        sys.exit(1)

    # Combine the sets of IP networks from the endpoints and extra routes
    ip_set = ip_set.union(extra_routes)

    # Generate route configuration lines and append them to the list of lines
    lines += generate_routes(ip_set, no_ipv4, no_ipv6)

    if args["--in-place"]:
        # If the --in-place flag is set, write the new configuration to the original file
        write_config(lines, args["<filename>"])
    else:
        # Otherwise, print the new configuration lines to stdout
        for line in lines:
            print(line)

    # Shutdown the logging system
    logging.shutdown()
