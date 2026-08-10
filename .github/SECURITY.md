# Security Policy

## Supported Versions

Only the latest tagged release of A13x is actively supported with fixes.

| Version | Supported |
| ------- | --------- |
| 3.5.x   | ✅        |
| < 3.5   | ❌        |

## Reporting a Vulnerability

A13x is a local, single-machine Maya pipeline tool — it does not run a
server, does not transmit data over a network, and does not handle
credentials or user accounts. Realistic risk is limited to things like:
the installer scripts writing to unintended filesystem locations, or a
maliciously crafted scene file triggering unexpected behavior in one of
the validation tools.

If you find an issue along those lines:

- **Do not** open a public issue describing the exploit in detail.
- Instead, open an issue titled "Security concern — details on request"
  with no technical specifics, or contact the maintainer directly via the
  contact details on [akshaydilipkumar.com](https://akshaydilipkumar.com).
- Please include the affected tool, Maya version, OS, and A13x version.

You should expect an initial response within a few days. This is a small,
single-maintainer project — response time may vary during coursework or
production deadlines.
