# vpn-config-gen #

[![GitHub Build Status](https://github.com/cisagov/vpn-config-gen/workflows/build/badge.svg)](https://github.com/cisagov/vpn-config-gen/actions)
[![CodeQL](https://github.com/cisagov/vpn-config-gen/workflows/CodeQL/badge.svg)](https://github.com/cisagov/vpn-config-gen/actions/workflows/codeql-analysis.yml)
[![Coverage Status](https://coveralls.io/repos/github/cisagov/vpn-config-gen/badge.svg?branch=develop)](https://coveralls.io/github/cisagov/vpn-config-gen?branch=develop)
[![Known Vulnerabilities](https://snyk.io/test/github/cisagov/vpn-config-gen/develop/badge.svg)](https://snyk.io/test/github/cisagov/vpn-config-gen)

```console
Update the routes of an OpenVPN configuration.

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
```

## Contributing ##

We welcome contributions!  Please see [`CONTRIBUTING.md`](CONTRIBUTING.md) for
details.

## License ##

This project is in the worldwide [public domain](LICENSE).

This project is in the public domain within the United States, and
copyright and related rights in the work worldwide are waived through
the [CC0 1.0 Universal public domain
dedication](https://creativecommons.org/publicdomain/zero/1.0/).

All contributions to this project will be released under the CC0
dedication. By submitting a pull request, you are agreeing to comply
with this waiver of copyright interest.
