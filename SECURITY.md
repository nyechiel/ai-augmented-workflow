# Security Policy

## Reporting a Vulnerability

This project handles OAuth tokens, API keys, and connections to personal email and chat services. Security issues are taken seriously.

If you discover a security vulnerability, please report it privately:

**Email:** <n.yechiel@gmail.com>

Please include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if you have one)

I'll acknowledge receipt within 48 hours and aim to provide a fix or mitigation within a week.

**Please do not file a public GitHub issue for security vulnerabilities.**

## Scope

Security issues in scope include:

- Credentials or secrets accidentally included in the repo
- Misconfigured defaults that expose sensitive data
- MCP proxy config that grants unintended write access
- Vulnerabilities in the bundled Crux or App Dashboard code
- Setup instructions that lead to insecure configurations

Out of scope:

- Vulnerabilities in upstream MCP servers (report to their maintainers)
- Vulnerabilities in Claude Code itself (report to Anthropic)
- Issues that require physical access to the user's machine
