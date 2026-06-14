# Customization Guide

This template is a starting point, not a finished product. The value comes from adapting it to your specific role, tools, and workflows. Here's how.

## 1. Customize CLAUDE.md

`CLAUDE.md` is the project instruction file - Claude Code reads it at the start of every session. It's the single most important file in the repo.

Start with `CLAUDE.md.example` and customize these sections:

**Protocol Rules** - Non-negotiable behaviors. Think about what would cause real damage if the agent did it wrong. Examples:
- "Never send messages" (if your chat/email tools are read-only)
- "Never create issues without confirmation" (if your issue tracker is visible to the org)
- "Never mark tasks done" (if you want a human review gate)

**Repo Structure** - Update to match your directory layout. The agent uses this to know where to put files.

**MCP Integrations** - List your connected tools, their capabilities, and any quirks. This is reference material the agent consults when using tools.

**Skills** - List your available skills with usage syntax so the agent (and you) can reference them quickly.

**Key Context** - Email addresses, account IDs, and other constants the agent needs repeatedly.

## 2. Choose Your MCP Servers

The included MCP stack covers a common knowledge worker workflow (email, calendar, chat, tasks). Your needs will differ.

Ask yourself: **What tools do I use daily?** Then find or build MCP servers for them.

Common categories:

| Category | This Template Uses | Alternatives |
|----------|-------------------|-------------|
| Email | Google Workspace MCP | Outlook MCP, Fastmail MCP |
| Chat | Slack MCP | Teams MCP, Discord MCP |
| Calendar | Google Workspace MCP | Outlook Calendar |
| Task board | Crux | Todoist MCP, Linear MCP, Asana MCP |
| Project tracker | *(not included)* | Jira (Rovo MCP), Linear MCP, GitHub Issues |
| Notes/Wiki | *(not included)* | Confluence (Rovo MCP), Notion MCP, Obsidian MCP |
| CRM | *(not included)* | Salesforce MCP, HubSpot MCP |
| Code hosting | *(not included)* | GitHub MCP, GitLab CLI |
| Data/Analytics | *(not included)* | Snowflake MCP, BigQuery, database MCPs |
| Health/Fitness | *(not included)* | Garmin MCP, Oura MCP, Whoop MCP |

For each new MCP server:
1. Add it to `local-mcp-stack/docker-compose.yml`
2. Add its secrets to `mcp-secrets.env`
3. Add its proxy route to `mcp-proxy-config.json`
4. Register it in `.mcp.json`
5. Document it in `CLAUDE.md` under MCP Integrations

## 3. Build Your Skills

Skills are reusable workflows that the agent executes when you type a slash command. They live in `.claude/skills/`.

Start with the included skills:
- **inbox-triage** - Process unread messages, extract action items
- **meeting-prep** - Generate pre-meeting briefs with context
- **capture** - Capture knowledge from meetings and documents
- **delegate** - Pick up a queued task, execute it, hand back for review
- **review** - End-of-day or end-of-week work review
- **learn** - Analyze corrections from the session, codify into rules

Before building from scratch, check what's already available. The skills format is becoming an industry standard - many enterprises are building internal skill marketplaces, and open-source collections are growing. Start by looking for existing skills you can drop in and customize, then create your own for workflows specific to your role.

Good candidates for custom skills:
- Any process you do weekly (status reports, pipeline reviews, on-call handoffs)
- Any multi-step task you explain to the agent more than twice
- Any workflow that touches multiple tools in sequence

**Skill ideas by role:**

| Role | Skill ideas |
|------|------------|
| Sales / Account Management | Deal prep (pull CRM data + recent emails before a call), pipeline review, account research, RFP response drafting |
| Marketing | Campaign brief, content calendar review, competitor monitoring, social listening digest |
| Engineering | PR review digest, on-call handoff summary, incident post-mortem, dependency audit |
| Research / Academia | Literature review, grant progress tracker, lab notebook capture, citation check |
| HR / Recruiting | Candidate brief (pull resume + LinkedIn + past interviews), offer comparison, onboarding checklist |
| Operations / Program Management | Status report, risk register update, vendor review, budget tracker |
| Customer Success | Account health check, renewal prep, escalation summary, QBR brief |

A skill is a markdown file (`SKILL.md`) in a subdirectory of `.claude/skills/`. The file contains instructions for the agent. See the included skills for the format.

## 4. Seed Your Memory

Memory files give the agent persistent context. Start with these:

**Essential (create first):**
- `user_profile.md` - Your role, team, company, focus areas
- `user_writing_style.md` - Tone, formatting preferences, things to avoid

**Recommended (add in week 1):**
- `reference_tools.md` - External tools, API endpoints, project keys
- `project_<your-product>.md` - Context about what you're building
- `user_schedule.md` - Your work days, timezone, availability

**Organic growth (add as you go):**
- `feedback_*.md` files - Every time you correct the agent on something that should be permanent, create a feedback memory
- `reference_*.md` files - Pointers to external systems, tools, and resources

See `memory/README.md` for the file format and more details.

## 5. Define Your Domains

Create domain directories for the areas you work in. Common starting points:
- `meetings/` - Meeting briefs and records
- `research/` - Market and competitive research

Your domains will differ based on your role:

**Sales example:**
- `accounts/acme-corp/` - Account history, contacts, deal notes
- `deals/` - Active opportunities, proposal drafts
- `competitive/` - Competitor positioning, battle cards

**Engineering example:**
- `services/api-gateway/` - Service-specific docs, runbooks
- `services/auth-service/` - Architecture decisions, on-call notes
- `incidents/` - Post-mortems, incident records

**Marketing example:**
- `campaigns/q3-launch/` - Campaign briefs, assets, results
- `content/` - Content calendar, drafts, style guide
- `competitive/` - Competitor messaging, market positioning

**Research example:**
- `projects/study-alpha/` - Active study files, protocols
- `literature/` - Paper summaries, citation notes
- `grants/` - Grant proposals, progress reports

The key is that each domain has a `knowledge.md` file that accumulates facts over time, and the agent knows where to file new information.

## 6. Set Your Templates

Templates live in `templates/` and provide consistent structure for recurring documents. The included set covers common knowledge worker needs:

- `meeting-brief.md` - Pre-meeting preparation (used by `/meeting-prep`)
- `meeting-record.md` - Post-meeting capture (used by `/capture`)
- `decision-record.md` - Decision documentation

Add templates for your own recurring document types (status reports, design docs, RFCs, post-mortems, etc.). The agent uses templates as starting points when skills create output files.

## Tips for Getting Started

1. **Start small.** Get CLAUDE.md, two memory files, and one skill working before adding complexity.
2. **Let feedback memories accumulate naturally.** Don't try to pre-write all the rules. Correct the agent, then codify the correction.
3. **Review your CLAUDE.md monthly.** It drifts as your workflow evolves. Remove stale sections and add new patterns.
4. **Copy skill patterns.** When creating a new skill, copy the structure of an existing one that works well.
5. **Test each MCP server independently.** Get one working before adding the next. Debugging a stack of broken services is miserable.
