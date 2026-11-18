# Security policy

## Supported versions

The project is in beta (0.x). Only the latest release receives security fixes.

## Reporting a vulnerability

Please report vulnerabilities **privately** through GitHub:
[Report a vulnerability](https://github.com/baranyit/bosch-compress6000-ha/security/advisories/new)
(repository **Security** tab, **Report a vulnerability**). Do not open a public issue or pull request
for a security problem.

Useful details: affected version, what an attacker needs (network position, access to Home Assistant),
the impact, and steps to reproduce. This is a maintenance-mode, single-maintainer project: expect an
acknowledgement within about a week and a fix or a mitigation plan as soon as practical.

## Scope

In scope: the integration code in `custom_components/bosch_compress6000`, including the gateway
crypto and protocol handling, the opt-in write path, diagnostics redaction, and the CI workflows.

Out of scope: vulnerabilities in the Bosch/Buderus gateway firmware or in Home Assistant itself
(report those to their vendors).

## Handling credentials

Never post real gateway addresses, gateway or private passwords, or full diagnostics dumps in an
issue, a pull request or a report. Credentials live only in the Home Assistant config entry;
diagnostics redact the host and passwords, and the repository and tests contain only obvious fakes.
