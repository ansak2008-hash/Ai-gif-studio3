# Security Policy

## Reporting a vulnerability

Please do not open a public issue for an undisclosed security vulnerability. Report security issues privately through the repository's configured GitHub security reporting channel when available.

Include the affected component, reproduction steps, impact, and any relevant logs without attaching secrets or personal data.

## Scope

The project treats external media, HTTP requests, Telegram payloads, and uploaded files as untrusted input. Security fixes should preserve the canonical validation and rendering contracts documented under `docs/security/`.
