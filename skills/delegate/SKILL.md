---
name: delegate
description: Pick up a task from Crux (or described inline), execute it autonomously, produce a deliverable, and set status to review. The agent never marks tasks done - the user is the final gate.
argument-hint: [Crux task ID or inline task description]
allowed-tools:
  - mcp__crux__get_task
  - mcp__crux__list_tasks
  - mcp__crux__move_task
  - mcp__crux__add_task
  - mcp__crux__add_comment
  - mcp__crux__assign_task
  - mcp__crux__edit_task
  - mcp__crux__search_tasks
  - mcp__google-workspace__search_gmail_messages
  - mcp__google-workspace__get_gmail_messages_content_batch
  - mcp__google-workspace__get_events
  - mcp__google-workspace__search_drive_files
  - mcp__google-workspace__get_doc_as_markdown
  - mcp__slack__conversations_search_messages
  - mcp__slack__conversations_replies
  - mcp__google-contacts__search_directory
  - WebSearch
  - WebFetch
  - Read
  - Write
  - Edit
  - Bash
  - Skill
---

# Task Delegation

Execute a task as the "Worker" agent. Produce a deliverable and hand it back for review.

Use `user_google_email: "{YOUR_EMAIL}"` for all Google Workspace calls.

## Workflow

### 1. Pick Up the Task

**If a Crux task ID is provided:** Fetch details, set status to "doing".

**If an inline description is provided:** Create a task in Crux with `status: "doing"`, `assignee: "Worker"`.

**If neither:** List Worker tasks in "todo" status and ask which to pick up.

### 2. Understand the Task

Confirm you understand:
- **What:** The specific deliverable
- **Where:** Where to save the output
- **Context:** Links to read, people involved

If ambiguous, ask one round of clarifying questions.

### 3. Execute

Common patterns:

| Task Type | Actions | Deliverable |
|-----------|---------|-------------|
| Reading | WebFetch the content, extract key points | Notes saved to `research/reading-notes/` |
| Research | Web search + repo grep + Slack/email search | Summary saved to `research/` |
| Document Draft | Read context, draft document | Saved to appropriate directory |
| Email/Message Draft | Read context, draft text | Presented in terminal for copy |

Log progress to the Crux task using `add_comment` at key moments.

### 4. Produce the Deliverable

Save file-based deliverables to the appropriate repo location. Present a summary of what was done and anything needing the user's attention.

### 5. Hand Off for Review

Set the task status to **"review"** and add a final comment:

```
## Done
- [what was accomplished, with file paths]

## For your review
- [ ] [specific action the user should take]
- [ ] Move to done or request revisions
```

**Never mark tasks done.** That is the user's decision after review.

## Rules

1. **Never create title-only tasks.** Always include origin and deliverable.
2. **Never skip the deliverable.** Every task produces a concrete output.
3. **Stay in scope.** Note adjacent work as a suggestion, don't do it.
4. **Fail loudly.** If blocked, set the task to "blocked" and explain what's needed.

## Graceful Degradation

| Scenario | Behavior |
|----------|----------|
| Crux unavailable | Work from inline description, present deliverable in terminal |
| Referenced tools unavailable | Note what you couldn't check, proceed with available tools |
