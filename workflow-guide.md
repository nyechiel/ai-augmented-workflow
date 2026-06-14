# Workflow Guide

How the pieces fit together in practice.

## Daily rhythm

The six included skills form a natural workflow loop:

```
Morning:    /capture          Auto-discover meeting notes, extract action items
            /inbox-triage     Triage unread Slack and Gmail (weekly or as needed)

Before:     /meeting-prep     Pre-meeting brief with context and talking points

During:     /delegate         Execute queued tasks from your task board

End of day: /review daily     Snapshot of what got done, what carries forward

Session end: /learn           Codify corrections from the session into rules
```

You don't need to run all of these every day. Start with `/capture` in the morning and `/review daily` at the end. Add the others as they become useful.

## How skills connect

Skills aren't isolated - they feed each other through shared files and the task board.

```
/inbox-triage ──creates tasks──> Crux ──picked up by──> /delegate
      |                           ^
      |                           |
/capture ──extracts action items──+
      |
      +──updates──> */knowledge.md ──read by──> /meeting-prep
      |
      +──updates──> stakeholders/  ──read by──> /meeting-prep, /inbox-triage
                                                  (for prioritization)

/learn ──updates──> memory/feedback_*.md ──read by──> all skills (via CLAUDE.md)
                    CLAUDE.md
                    skills/*/SKILL.md

/review ──reads──> Crux (completed tasks)
                   meetings/ (today's meetings)
```

The key connections:

- **Triage and capture create tasks.** `/inbox-triage` extracts action items from messages. `/capture` extracts them from meeting notes. Both land in Crux.
- **Delegate consumes tasks.** `/delegate` picks up queued tasks, executes them, and sets them to "review" for your approval.
- **Capture builds knowledge.** Facts, decisions, and contacts discovered during capture flow into domain knowledge files and the stakeholder map.
- **Meeting prep reads knowledge.** Before a meeting, `/meeting-prep` pulls context from knowledge files, stakeholders, prior meetings, and the task board.
- **Learn improves everything.** Corrections you make during any session get codified into memory files, CLAUDE.md rules, or skill instructions - making all future sessions better.
- **Review closes the loop.** `/review` summarizes the day's or week's output from Crux, calendar, and Slack activity.

## Where things are saved

| Output | Location |
|--------|----------|
| Meeting briefs (pre-meeting) | `meetings/YYYY-MM-DD-<topic>.md` |
| Meeting records (post-meeting) | `meetings/YYYY-MM-DD-<topic>.md` |
| Reading notes | `research/reading-notes/<slug>.md` |
| Domain knowledge | `<domain>/knowledge.md` |
| Decision records | `<domain>/decisions/<slug>.md` |
| Stakeholder map | `stakeholders/README.md` |
| Inbox triage logs | `triages/inbox-triage-<date>.md` |
| Daily reviews | `reviews/daily-review-YYYY-MM-DD.md` |
| Weekly reviews | `reviews/week-review-YYYY-MM-DD.md` |

Create directories as needed. The agent will use these paths by convention.

## Key conventions

**Human-as-approver.** The agent drafts, researches, and prepares. You decide and send. No messages are sent automatically. No issues created in external systems without your confirmation.

**Task lifecycle.** Tasks flow through: `todo` -> `doing` -> `review` -> `done`. The agent sets tasks to "review" when work is complete. Only you move them to "done" after checking the output.

**Assignee convention.** Use your name for tasks you'll do yourself. Use "Worker" for tasks the agent should pick up via `/delegate`.

**Skill tool boundaries.** Each skill has an `allowed-tools` list in its frontmatter. This is a security boundary - the skill can only access the tools listed. Even if a skill's instructions were somehow corrupted, the tool allowlist holds.

## Building your own rhythm

The daily rhythm above is a starting point. As you use the system, you'll discover your own patterns:

- **Which skills you run daily vs. weekly.** Some people triage every morning; others batch it on Mondays.
- **What new skills you need.** If you find yourself repeating a multi-step workflow, encode it as a skill.
- **What knowledge files emerge.** Your domains, stakeholders, and templates will reflect your specific role.
- **What feedback accumulates.** Memory files build up over weeks, making the agent increasingly tuned to how you work.

The system gets better the more you use it. The first week is clunky. By week four, it feels like a different tool.
