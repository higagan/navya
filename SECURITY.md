# Security Policy

## Supported Versions

This project is pre-alpha and has no tagged releases yet. Security fixes
land on `main`.

## Reporting a Vulnerability

Please do not open a public issue for security vulnerabilities. Instead,
use [GitHub's private vulnerability reporting](https://github.com/higagan/navya/security/advisories/new)
for this repository, or contact the maintainer directly via
[@higagan](https://github.com/higagan).

Please include:
- A description of the issue and its impact
- Steps to reproduce, or a proof of concept
- Any suggested remediation, if you have one

We'll acknowledge reports within a few days and aim to ship a fix or
mitigation before any public disclosure.

## Scope notes

- This project calls third-party OCR/LLM APIs (Google Cloud Vision,
  Anthropic, and potentially others). Credentials are configured via `.env`
  files, which are gitignored — never commit real API keys. If you find one
  committed in history, please report it as above so it can be rotated.
