# vpn-config-gen #

[![GitHub Build Status](https://github.com/cisagov/vpn-config-gen/workflows/build/badge.svg)](https://github.com/cisagov/vpn-config-gen/actions)
[![Coverage Status](https://coveralls.io/repos/github/cisagov/vpn-config-gen/badge.svg?branch=develop)](https://coveralls.io/github/cisagov/vpn-config-gen?branch=develop)
[![Total alerts](https://img.shields.io/lgtm/alerts/g/cisagov/vpn-config-gen.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/cisagov/vpn-config-gen/alerts/)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/cisagov/vpn-config-gen.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/cisagov/vpn-config-gen/context:python)
[![Known Vulnerabilities](https://snyk.io/test/github/cisagov/vpn-config-gen/develop/badge.svg)](https://snyk.io/test/github/cisagov/vpn-config-gen)

```console
Update the routes of an OpenVPN configuration.

There are certain internet services that filter access based on egress.
This tool will update the routes of an OpenVPN configuration file to include
the latest routes for those IP addresses.

Usage:
  vpnconf [--log-level=LEVEL] [--in-place] <filename>
  vpnconf (-h | --help)

Options:
  -h --help              Show this message.
  -i --in-place          Update file in place.
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
