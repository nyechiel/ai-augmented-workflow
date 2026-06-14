---
name: meeting-prep
description: Generate a pre-meeting brief with context discovery, commitment tracking, and talking points.
argument-hint: [topic] [attendee1, attendee2, ...]
allowed-tools:
  - mcp__google-workspace__get_events
  - mcp__google-workspace__search_gmail_messages
  - mcp__google-workspace__get_gmail_messages_content_batch
  - mcp__google-workspace__search_drive_files
  - mcp__google-workspace__get_doc_as_markdown
  - mcp__slack__users_search
  - mcp__slack__conversations_search_messages
  - mcp__slack__conversations_replies
  - mcp__time__get_current_time
  - mcp__google-contacts__search_directory
  - mcp__crux__search_tasks
  - mcp__crux__list_tasks
  - Read
  - Write
  - Edit
  - Bash
---

# Meeting Prep

Generate a meeting brief by discovering context across all available tools.

Use `user_google_email: "{YOUR_EMAIL}"` for all Google Workspace calls.

## Workflow

### 1. Determine Meeting Target

- If the user provides a topic and/or attendees, use those directly.
- Otherwise, use `get_events` with `detailed: true` to list upcoming meetings. Filter out declined and all-day events. Ask which one to prep for.
- Check time to meeting via `get_current_time`. If less than 15 minutes away, produce a fast brief (attendees + key context only).

### 2. Context Discovery (run in parallel)

#### A. Stakeholder Context
- Check `stakeholders/README.md` for notes on each attendee.
- For unknown attendees, look up via `search_directory` and add to stakeholder map.
- Search recent emails and Slack messages with key attendees (last 7 days).

#### B. Meeting History
- Search `meetings/` for previous meeting files with the same attendees or topic.
- Extract unchecked action items and deferred topics from prior meetings.

#### C. Domain Knowledge
- Grep `*/knowledge.md` files for meeting topic keywords.
- Check `<domain>/decisions/` for prior decisions on the topic.

#### D. Task Board Context
- Search Crux for tasks related to the meeting topic or attendees.

### 3. Generate the Brief

Save to `meetings/YYYY-MM-DD-<topic-slug>.md` using `templates/meeting-brief.md`:

```markdown
# Meeting Brief: [Title]

**Date/Time:** [date and time]
**Attendees:** [names and titles]

## Quick Context
- [1-2 sentences: what this is about and why it matters]

## What They Expect from You
- [ ] [Commitments or deliverables they're waiting on]

## Suggested Follow-Up Questions
1. [Question that advances the discussion]
```

### 4. Present Summary

After saving, present: key things to be aware of, outstanding commitments, and top 3 talking points.

## Graceful Degradation

| Tool | If unavailable |
|------|---------------|
| Calendar | Skip calendar lookup. User must provide topic and attendees. |
| Gmail/Slack | Skip email/message search. Note gap. |
| Crux | Skip task board search. Note gap. |

## Key Principles

- **"What do they expect from me?"** is the most important section.
- **Scannable in under 2 minutes.** Bullet points, no filler.
- **Link everything.** Make it easy to jump to sources.
