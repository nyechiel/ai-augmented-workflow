# AI-Augmented Workflow

**Give your AI agent full context about your work - email, calendar, chat, tasks, documents - and let it execute multi-step workflows on your behalf, with you as the approver.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Linux | macOS | WSL2](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20WSL2-lightgrey.svg)](#platform-notes)
[![Built with Claude Code](https://img.shields.io/badge/Built%20with-Claude%20Code-blueviolet.svg)](https://claude.ai/claude-code)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-orange.svg)](https://modelcontextprotocol.io/)

A template you clone, customize, and make your own. Built on [Claude Code](https://claude.ai/claude-code) and [MCP](https://modelcontextprotocol.io/), but the architecture - skills as markdown, memory files, tool allowlists - is portable to any MCP-compatible agent.

## Table of contents

- [What's included](#whats-included)
- [Architecture](#architecture)
- [Quick start](#quick-start)
- [Included skills](#included-skills)
- [Key design decisions](#key-design-decisions)
- [Important considerations](#important-considerations)
- [Adapting to your role](#adapting-to-your-role)
- [Platform notes](#platform-notes)
- [Further reading](#further-reading)
- [Contributing](#contributing)
- [Acknowledgments](#acknowledgments)
- [License](#license)

## What's included

| Layer | What it does | Key files |
|-------|-------------|-----------|
| **Rules** | Defines agent behavior, boundaries, and knowledge | `CLAUDE.md.example` |
| **Infrastructure** | Connects Claude Code to your tools via MCP | `local-mcp-stack/`, `.mcp.json.example` |
| **Skills** | Reusable multi-step workflows (inbox triage, meeting prep, etc.) | `skills/` |
| **Memory** | Persistent cross-session context about you and your work | `memory/` |
| **Templates** | Starting points for recurring documents | `templates/` |
| **Ops** | Task board, backup, recovery, and service management | `crux/`, `scripts/`, `app-dashboard/` |

## Architecture

```
You (human-as-approver)
  |
  v
Claude Code (agent)
  |
  +-- CLAUDE.md (rules, boundaries, knowledge)
  +-- Skills (inbox-triage, meeting-prep, capture, delegate, review, learn)
  +-- Memory (user profile, feedback, project context, references)
  |
  +-- App Dashboard (localhost:9000 - manages all services below)
  |
  +-- MCP Proxy Gateway (localhost:9090)
  |     +-- Google Workspace (Gmail, Calendar, Drive, Docs)
  |     +-- Slack (messages, threads, unreads, search)
  |     +-- Google Contacts (directory lookup)
  |     +-- Time (timezone-aware clock)
  |     +-- ... (add your own)
  |
  +-- Crux (task board - stdio MCP)
```

The proxy gateway aggregates all MCP servers behind a single endpoint with **tool allowlists** - your safety net for enforcing read-only access even when servers have write capabilities.

## Quick start

```bash
git clone https://github.com/YOUR_USERNAME/ai-augmented-workflow.git
cd ai-augmented-workflow
./scripts/setup.sh        # Linux/macOS/WSL2
# or: .\scripts\setup.ps1  # Windows PowerShell
```

The setup script installs Crux and App Dashboard, copies example configs, creates symlinks, and tells you what's left to do manually (MCP server setup, credentials, customization).

See [docs/SETUP.md](docs/SETUP.md) for the full step-by-step guide.

## Included skills

These are starter skills to get you up and running. They cover common knowledge worker workflows, but the real value comes from building your own for whatever you repeat. A skill is just a markdown file with instructions - if you can explain it to a person, you can encode it as a skill.

| Skill | What it does |
|-------|-------------|
| `/inbox-triage` | Triage unread Slack and Gmail, categorize into respond/review/FYI/defer, extract action items |
| `/meeting-prep` | Generate a pre-meeting brief with context, prior interactions, and talking points |
| `/capture` | Auto-discover meeting notes, capture facts/links/contacts, extract action items |
| `/delegate` | Pick up a queued task, execute it, hand back for review |
| `/review` | End-of-day or end-of-week review with work output, wins, and risks |
| `/learn` | Analyze corrections from the session and codify them into memory |

Each skill is a SKILL.md file with a tool allowlist and workflow steps. See [skills/README.md](skills/README.md) for how to create your own.

## Key design decisions

**Human-as-approver.** The agent drafts, researches, and prepares - you decide and send. No messages are ever sent automatically. No issues created without confirmation. This isn't a limitation; it's the trust model that makes the system usable for real work.

**Read-mostly access.** MCP servers are configured with tool allowlists that restrict the agent to read-only access for most integrations. Write access is limited to task management (Crux) and email label management (archive/organize). The proxy config (`mcp-proxy-config.json`) is where you control this.

**Local-first.** Everything runs on your machine. No cloud services beyond the APIs you're already using (Gmail, Slack). Your knowledge base, task history, and memory stay in a git repo you control.

**Skills over prompts.** Instead of re-explaining workflows every session, skills encode them as reusable SKILL.md files with explicit tool allowlists and step-by-step instructions. The agent follows the skill; you review the output.

<details>
<summary><h2>Important considerations</h2></summary>

This system connects an AI agent to your real email, calendar, chat, and task management. While it's designed with safety boundaries (tool allowlists, read-only defaults, human-as-approver), you are responsible for understanding what access you're granting and reviewing what the agent does with it.

A few things to keep in mind:

- **Credentials are sensitive.** OAuth tokens and API keys in `mcp-secrets.env` grant access to your accounts. Treat this file like a password. Never commit it to git.
- **Review tool allowlists carefully.** The proxy config (`mcp-proxy-config.json`) controls which MCP tools are exposed. Before starting the stack, verify you're comfortable with what's enabled - especially any write operations.
- **Enterprise environments have rules.** If you're connecting to corporate systems (work email, company Slack, internal trackers), check with your IT and security teams first. Many organizations have policies about third-party tool access, API token usage, data handling, and AI tool adoption that may apply.
- **AI output requires judgment.** The agent can misread context, misattribute information, or produce plausible-sounding errors. The human-as-approver model exists because human review is not optional - it's the safety mechanism.

</details>

<details>
<summary><h2>Adapting to your role</h2></summary>

This template works for any knowledge worker role. What changes:

- **Your MCP servers** - Connect the tools you actually use (Jira, Salesforce, HubSpot, Notion, Confluence, GitHub, etc.)
- **Your skills** - Build workflows for what you repeat. A few examples by role:
  - **Sales/account management:** deal prep, pipeline review, account research, RFP drafting
  - **Marketing:** campaign brief, content calendar review, competitor monitoring
  - **Engineering:** PR review digest, on-call handoff, incident summary
  - **Research/academia:** literature review, grant progress tracker, lab notebook capture
  - **Operations/program management:** status report, risk register update, vendor review
- **Your memory** - Seed it with your role, domain, and preferences
- **Your templates** - Documents you create regularly (proposals, reports, briefs, post-mortems, etc.)

See [docs/CUSTOMIZATION.md](docs/CUSTOMIZATION.md) for a detailed guide, and [workflow-guide.md](workflow-guide.md) for how the skills connect and a suggested daily rhythm.

</details>

<details>
<summary><h2>Platform notes</h2></summary>

This template is tuned for Linux (Fedora), but the core workflow (Claude Code, MCP servers, skills, memory) works on any platform. The OS-specific parts are the infrastructure layer:

| Component | Linux (included) | macOS | Windows |
|-----------|-----------------|-------|---------|
| Containers | Podman + podman-compose | Docker Desktop or Podman Machine | Docker Desktop or WSL2 + Podman |
| Service management | systemd user services | launchd plist files | Task Scheduler or WSL2 systemd |
| Backup timer | systemd timer | launchd plist with `StartCalendarInterval` | Task Scheduler |
| Shell scripts | bash (native) | bash (native) | WSL2 or Git Bash |

If you're on macOS or Windows, swap the systemd service files for your platform's equivalent and use Docker instead of Podman. Everything else works as-is.

</details>

## Further reading

This workflow grew out of daily use over several months. The companion blog post walks through the concepts and what I learned building it:

- [Build Your Own AI-Augmented Workflow](https://nyechiel.com/blog/2026/06/14/build-your-own-ai-augmented-workflow/) - concepts, architecture, and lessons learned
- [Building an AI Operating System for Product Management](https://nyechiel.com/blog/2026/05/13/ai-operating-system-for-product-management/) - the earlier post that describes the system from the user's perspective

## Contributing

Contributions are welcome - bug fixes, documentation improvements, new skill examples, and platform compatibility patches. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines and [SECURITY.md](SECURITY.md) for reporting vulnerabilities.

## Acknowledgments

This project builds on ideas and tools from several people:

- [Andrej Karpathy](https://karpathy.ai/) - His [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) concept (compiling raw data into structured, interlinked markdown rather than chunking it into vector embeddings) is the knowledge architecture pattern behind this workflow. His observations on LLM coding pitfalls, [codified by the community](https://github.com/multica-ai/andrej-karpathy-skills), also helped establish structured project instructions as a best practice.
- [Anthropic](https://www.anthropic.com/) - Claude Code, the skills system, and the original creators of the [Model Context Protocol](https://modelcontextprotocol.io/), now an open standard under the [Linux Foundation's Agentic AI Foundation](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation).
- [TBXark](https://github.com/TBXark) - [mcp-proxy](https://github.com/TBXark/mcp-proxy), the gateway that makes tool allowlists possible - a key safety component.
- [Boris Cherny](https://github.com/bcherny) - Creator of Claude Code. His [workflow tips](https://howborisusesclaudecode.com/) and approach to CLAUDE.md as a living team document were an early reference for structuring agent instructions.
- [Jonathan Zarecki](https://github.com/jonzarecki) - His work on a similar AI-augmented workflow was a direct inspiration for this project.

## License

[MIT](LICENSE). Clone it, customize it, build on it - no restrictions beyond preserving the license notice.
