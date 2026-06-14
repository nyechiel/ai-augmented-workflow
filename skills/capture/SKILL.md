---
name: capture
description: Auto-discover unprocessed meeting notes and transcripts, capture ad-hoc thoughts and facts, or manually capture key facts from a session. Keeps domain knowledge files up to date.
argument-hint: [optional: domain | 1d | 3d | 7d | meeting name(s) | free-form text]
allowed-tools:
  - mcp__google-workspace__search_gmail_messages
  - mcp__google-workspace__get_gmail_messages_content_batch
  - mcp__google-workspace__get_gmail_message_content
  - mcp__google-workspace__search_drive_files
  - mcp__google-workspace__get_doc_as_markdown
  - mcp__google-workspace__get_events
  - mcp__google-contacts__search_directory
  - mcp__time__get_current_time
  - mcp__slack__conversations_search_messages
  - mcp__slack__conversations_replies
  - mcp__crux__add_task
  - mcp__crux__search_tasks
  - mcp__google-workspace__modify_gmail_message_labels
  - Read
  - Write
  - Edit
  - Bash
---

# Knowledge Capture

Auto-discover unprocessed meeting notes and shared documents, capture ad-hoc thoughts, or manually capture key facts into the right places in the repo.

Use `user_google_email: "{YOUR_EMAIL}"` for all Google Workspace calls.

## Workflow

### 1. Determine Mode

Parse the argument:

- **No argument** - scan calendar and inbox for meetings with uncaptured notes (last 24h)
- **Time window** (e.g., `3d`, `7d`) - scan with that lookback period
- **Domain name** (matches a directory with `knowledge.md`) - interactive capture for that domain
- **Meeting name(s)** - search for that specific meeting's notes
- **Free-form text** - classify and route immediately (URL, fact, action item, contact)

### 2. Auto-Discovery (no argument or time window)

1. Use `get_current_time` for today's date
2. Use `get_events` to list meetings in the time window
3. For each meeting, search Gmail for automated notes (`"meeting notes" subject:"<title>"`)
4. If notes found, read the linked Google Doc via `get_doc_as_markdown` (not just the email summary)
5. Check `meetings/` for existing capture files to avoid re-processing
6. Present discovered meetings and ask which to process

### 3. Process Meeting Content

For each meeting being processed, extract:
- **Action items** assigned to you - create Crux tasks with label `action-item`
- **Decisions made** - route to decision records if explicit choices were made
- **Key facts** - route to domain knowledge
- **New contacts** - look up via `search_directory`, add to stakeholders

### 4. Classify Each Fact

Every piece of knowledge goes to exactly one place:

| Type | Where |
|------|-------|
| Decision | `{domain}/decisions/<slug>.md` (use template) |
| Domain knowledge | `{domain}/knowledge.md` |
| Stakeholder context | `stakeholders/README.md` |
| Cross-session context | `memory/` files |

### 5. Update Domain Knowledge

Append to `{domain}/knowledge.md`:

```markdown
### [Topic] - [date]

[Fact, stated concisely. One paragraph max.]

**Source:** [Meeting brief link, doc link, or "verbal from [person]"]
```

Rules: append don't rewrite, one fact per entry, include source, deduplicate.

### 6. Generate Meeting Record

Save to `meetings/YYYY-MM-DD-<topic-slug>.md` using `templates/meeting-record.md`. If a prep brief already exists from `/meeting-prep`, update it instead of creating a new file.

### 7. Confirm Capture

Present a summary: what was captured, where it was saved, any Crux tasks created, any new stakeholders added.

## Graceful Degradation

| Scenario | Behavior |
|----------|----------|
| Calendar unavailable | Gmail-only discovery |
| Gmail unavailable | Calendar-only, scan Drive |
| Both unavailable | Fall back to interactive flow |

## Key Principles

- **Auto-discover first, ask second.** Scan calendar and inbox rather than asking questions.
- **Facts over summaries.** "Auth team owns SSO, target June 15" beats "We discussed SSO plans."
- **Source everything.** If you can't trace it back, it's not knowledge.
