# Skills

Skills are reusable workflows for [Claude Code](https://claude.ai/claude-code). Each skill is a markdown file (`SKILL.md`) with YAML frontmatter that defines what the skill does, what tools it can use, and a step-by-step workflow.

## Anatomy of a skill

```yaml
---
name: my-skill
description: What this skill does and when to use it.
argument-hint: [what the user can pass as arguments]
allowed-tools:
  - mcp__slack__conversations_unreads
  - mcp__google-workspace__search_gmail_messages
  - mcp__crux__add_task
  - Read
  - Write
---
```

**Frontmatter fields:**

| Field | Required | Purpose |
|-------|----------|---------|
| `name` | Yes | Skill identifier (matches the directory name) |
| `description` | Yes | What it does and when to use it |
| `argument-hint` | No | Hint for what arguments the user can pass |
| `allowed-tools` | Yes | Whitelist of tools the skill can use - this is a security boundary |

The body is markdown describing the workflow: steps, graceful degradation, and key principles.

## How to create your own

1. Create a directory under `.claude/skills/` (e.g., `.claude/skills/my-skill/`)
2. Create a `SKILL.md` with YAML frontmatter and workflow steps
3. Test by typing `/my-skill` in Claude Code

**Tips:**
- Start with the `allowed-tools` from a similar skill and adjust
- Use placeholders like `{YOUR_EMAIL}` for values that vary per user
- Include a Graceful Degradation table so the skill works with partial MCP availability

## Included skills

| Skill | What it does |
|-------|-------------|
| **inbox-triage** | Triage unread Slack and Gmail into Respond/Review/FYI/Defer, extract action items into Crux |
| **meeting-prep** | Generate a pre-meeting brief with context, prior interactions, and talking points |
| **capture** | Auto-discover meeting notes, capture facts and knowledge into the right files |
| **delegate** | Pick up a queued task, execute it, hand back for review |
| **review** | End-of-day or end-of-week work review |
| **learn** | Analyze corrections from the session, codify them into memory or rules |

## Customization

1. **Replace placeholders:** Search for `{YOUR_EMAIL}` and `{YOUR_NAME}` and replace with your values
2. **Adjust allowed-tools:** Add or remove MCP tools based on what you have connected
3. **Add domain knowledge:** Create `<domain>/knowledge.md` files - skills like `capture` and `meeting-prep` will use them automatically
4. **Set up stakeholders:** Create `stakeholders/README.md` with key contacts for prioritization

## Prerequisites

These skills assume the following MCP integrations (all optional - skills degrade gracefully):

- **Slack** - channel history, unreads, search
- **Google Workspace** - Gmail, Calendar, Drive, Docs
- **Crux** (or similar task manager) - task CRUD, search
- **Google Contacts** - directory search for name/title lookups
- **Time** - timezone-aware current time
