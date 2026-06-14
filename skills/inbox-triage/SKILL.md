---
name: inbox-triage
description: Triage unread Slack and Gmail into respond/review/FYI/defer. Extracts action items into Crux, archives processed emails, produces summary with draft responses.
argument-hint: [optional: slack | gmail | all (default)]
allowed-tools:
  - mcp__slack__conversations_unreads
  - mcp__slack__activity_unreads
  - mcp__slack__saved_list
  - mcp__slack__conversations_replies
  - mcp__slack__saved_update
  - mcp__google-workspace__search_gmail_messages
  - mcp__google-workspace__get_gmail_messages_content_batch
  - mcp__google-workspace__get_gmail_message_content
  - mcp__google-workspace__modify_gmail_message_labels
  - mcp__google-workspace__get_events
  - mcp__google-contacts__search_directory
  - mcp__crux__add_task
  - mcp__crux__list_tasks
  - mcp__crux__search_tasks
  - mcp__time__get_current_time
  - mcp__slack__channels_list
  - mcp__slack__conversations_mark
  - mcp__slack__activity_mark_read
  - Read
  - Write
  - Edit
  - Bash
---

# Inbox Triage

Scan Slack and/or Gmail for unread messages, categorize them, and produce an actionable triage summary.

## Workflow

### 1. Determine Scope

Use `get_current_time` to get today's date. Based on the argument:
- `slack` - Slack only
- `gmail` - Gmail only
- `all` or no argument - both (default)

### 2. Slack Triage

#### A. Gather Unread Messages

- Use `conversations_unreads` with `include_messages: true` to get all unread messages.
- Use `activity_unreads` to get @mentions and thread replies.
- For any unread message in a thread, use `conversations_replies` to read the full thread. Decisions live in replies - never categorize from top-level messages alone.

#### B. Categorize Each Item

| Category | Criteria |
|----------|----------|
| **Respond** | Direct question, request for input, blocking someone |
| **Review** | Shared document, PR, proposal needing your eyes |
| **FYI** | Announcement, status update, no action needed |
| **Defer** | Interesting but needs research before responding |

#### C. Prioritize Respond Items

Rank by: manager/direct stakeholders > people blocked on you > time-sensitive > others.

#### D. Extract Action Items

Scan Respond and Review items for work that needs tracking beyond a quick reply. For each:
1. Dedup against existing Crux tasks via `search_tasks`
2. Create via `add_task` with `assignee: "{YOUR_NAME}"`, `labels: ["action-item"]`, appropriate priority and estimate

### 3. Gmail Triage

Use `user_google_email: "{YOUR_EMAIL}"` for all Gmail calls.

#### A. Gather Unread Emails

- Search with `is:unread -category:promotions -category:social -category:updates`. **Paginate fully** - Gmail returns max 10 per page.
- Fetch message bodies via `get_gmail_messages_content_batch` (max 25 per batch).
- Skip automated notifications and bulk mail unless they mention you by name.

#### B. Detect Self-Sent Emails

Search for self-sent emails (`from:{YOUR_EMAIL} to:{YOUR_EMAIL} is:unread`). These are capture requests, not regular inbox items. For each:
1. Create a Crux task (label `reading` for URLs, `self-capture` for notes)
2. Archive the email after task creation

#### C. Categorize and Prioritize

Same categories as Slack. Additional signals:
- CC vs TO: If on CC, lean toward FYI unless explicitly asked for input
- Reply-all threads with >5 participants and no name mention: lean FYI

#### D. Extract Action Items

Same logic as Slack - scan for work that needs Crux tracking.

### 4. Cross-Reference

- Identify duplicates across Slack and Gmail - consolidate into one item
- Connect items to today's calendar events

### 5. Generate Triage Summary

Present in terminal and save to `triages/inbox-triage-YYYY-MM-DD.md`:

```
## Inbox Triage - [date] [time]

**Sources:** Slack [checked/unavailable] | Gmail [checked/unavailable]

### Respond ([count])
1. **[Source]** from **[Person]** ([time ago]) ([link])
   > [Summary of what they need]
   **Suggested response:** [Draft reply]

### Review ([count])
- **[Source]** from **[Person]** ([link]): [Summary]

### FYI ([count])
- **[Source]** from [Person] ([link]) - [1-line summary]

### Defer ([count])
- **[Source]** from **[Person]**: [Summary + why deferred]

### Action Items Created ([count])
- Crux #[ID]: **[Title]** ([priority])

### Self-Captures ([count], if any)
- **[Subject]** - Created Crux #ID - archived
```

### 6. Post-Triage Housekeeping

- **Archive processed emails**: FYI and Review emails where action is offline. Keep emails awaiting a reply in inbox.
- **Mark Slack as read**: FYI items and Review items where action is offline. Keep messages awaiting your reply unread.

## Graceful Degradation

| Scenario | Behavior |
|----------|----------|
| Slack MCP unavailable | Skip Slack, run Gmail only (or vice versa) |
| Both unavailable | Cannot proceed |
| Too many unreads (>100) | Scan last 24 hours only, note skipped messages |
| Crux unavailable | List action items in summary with "track manually" note |

## Key Principles

- **Draft responses, don't send.** MCP integrations are read-only.
- **Thread-aware.** A message that looks FYI in isolation might be Respond in a thread where you committed to something.
- **Time-bounded.** Default to last 24 hours.
- **No false urgency.** A good triage has more FYI items than Respond items.
