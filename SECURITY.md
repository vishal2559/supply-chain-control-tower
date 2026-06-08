# Security Policy

## Project: Supply Chain Control Tower

**Owner:** Vishal

**Repository:** https://github.com/vishal2559/supply-chain-control-tower

---

## Supported Versions

This project is actively maintained. Security fixes are applied to the latest version on the `main` branch.

| Version              | Supported                                |
| -------------------- | ---------------------------------------- |
| Latest `main` branch | Yes                                      |
| Older commits        | No — please update to the latest version |

---

## Security Scope

The **Supply Chain Control Tower** is a local demo/community project designed to run on a user's own machine.

The project is intended for learning, portfolio, open technical contribution, and architecture demonstration purposes. It uses sample/demo data and local configuration.

Security considerations covered by this project include:

1. **No committed secrets**

   API keys, tokens, credentials, and local `.env` files should never be committed to GitHub.

2. **Sample/demo data only**

   The public repository should not contain real customer data, private company data, or sensitive operational records.

3. **Configuration separation**

   Public-safe configuration can be included for demo use. Private credentials, local overrides, and sensitive values should be stored in `.env` files or ignored local configuration files.

4. **Read-only data access pattern**

   The project is designed around local analysis and demo-oriented data access. Tools should avoid destructive database operations unless explicitly required for setup or controlled maintenance scripts.

5. **Input validation**

   User inputs passed into MCP tools should be validated before processing.

6. **Prompt-injection awareness**

   Data returned from files or databases should be treated as data, not instructions. Tool outputs should be handled carefully before being passed to Claude.

7. **Audit and observability**

   Where available, tool calls, performance events, and anomalies may be logged locally to support debugging and review.

---

## Reporting a Vulnerability

Please do **not** open a public GitHub issue for security vulnerabilities.

To report a vulnerability privately:

1. Go to the **Security** tab on this repository.
2. Choose **Report a vulnerability** if available.
3. Describe the issue and steps to reproduce it.

I will make a reasonable effort to review reports within **72 hours** and address confirmed issues in a future update.

---

## What to Include in a Report

A helpful report should include:

* Description of the issue
* Steps to reproduce
* Expected behavior
* Actual behavior
* Potential impact
* Suggested fix, if available

---

## Out of Scope

The following are generally out of scope for this demo project:

* Issues requiring physical access to the user's machine
* Denial-of-service against a local-only process
* Findings from automated scanners without demonstrated impact
* Vulnerabilities in third-party libraries that should be reported upstream
* Misconfiguration caused by committing local secrets or `.env` files manually

---

## Secret Handling

Do not commit files that contain:

* API keys
* Access tokens
* Passwords
* Private database files
* Real customer data
* Private company data
* Local machine paths with sensitive information
* Personal project memory or private planning notes

Recommended `.gitignore` entries include:

```gitignore
.env
.env.*
*.db
logs/
memory/project_memory.json
_private_backup_original/
*_PRIVATE.md
```

If a secret is accidentally committed, remove it from the repository and rotate the exposed credential immediately.

---

## Acknowledgements

Security researchers or contributors who responsibly disclose valid issues may be acknowledged in release notes with their permission.

---

*This policy is intended for the public demo/community edition of the Supply Chain Control Tower project.*
