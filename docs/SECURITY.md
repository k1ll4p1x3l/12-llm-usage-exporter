# Security Policy for llm-usage-exporter

## Commitments

This project is pre-alpha and not intended for handling secrets or regulated production reporting.

## Immutable security boundaries

- No credential storage, decoding, forwarding, or proxying.
- No login/refresh token operations.
- No parsing of local provider credential blobs outside explicit policy test fixtures.
- No scraping or MITM data collection.
- GitHub metadata/settings helpers are permanently contact-free previews; they
  contain no dynamic shell evaluation and reject apply mode.
- Public-safety findings report only path, line, and finding class. Suspected
  credential values are never echoed back to CI logs.
- Release publication is gated by race tests plus an unpublished six-platform
  archive, checksum, and SBOM verification run.

## Policy violations

Any change that reads provider credentials (for example `~/.codex/auth.json`) outside explicit deny-list tests is a security regression.

## Reporting

File a private security report with:

- Affected version
- OS and architecture
- Steps to reproduce
- Logs with secrets removed
