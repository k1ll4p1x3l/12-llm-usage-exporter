# Security Policy

## Supported Versions

Pre-Alpha has no security support commitment. Do not use for production secrets or compliance reporting until a signed release exists.

## Security Boundaries

This project must never manage, store, refresh, rotate, copy, decode, proxy, or exfiltrate provider credentials. If a change reads credential files such as `~/.codex/auth.json`, it is considered a security bug unless explicitly limited to denylist tests.

## Reporting a Vulnerability

Open a private security advisory in GitHub. Include provider, version, operating system, logs with secrets removed, and reproduction steps.

## Non-goals

- Bypassing quotas or usage limits
- Sharing provider sessions between users
- Extracting tokens from local CLIs
- Acting as OAuth client for providers
