---
name: review
description: End-of-day or end-of-week review covering work output, wins/risks/opportunities. Weekly output is sharable with your manager.
argument-hint: daily | weekly
allowed-tools:
  - mcp__crux__list_tasks
  - mcp__crux__search_tasks
  - mcp__crux__get_task
  - mcp__google-workspace__get_events
  - mcp__slack__conversations_search_messages
  - mcp__slack__conversations_replies
  - mcp__time__get_current_time
  - Read
  - Write
  - Edit
  - Bash
---

# Review

End-of-day or end-of-week review covering work output and forward planning.

Use `user_google_email: "{YOUR_EMAIL}"` for all Google Workspace calls.

## Modes

| Mode | Scope | Output |
|------|-------|--------|
| `daily` (default) | Today's work | `reviews/daily-review-YYYY-MM-DD.md` |
| `weekly` | Rolling 7 days | `reviews/week-review-YYYY-MM-DD.md` |

## Workflow: Daily Review

### 1. Gather Today's Data

Use `get_current_time` for today's date. Run in parallel:

- **Crux tasks:** `list_tasks(status="done")` filtered by today, plus doing/review counts
- **Calendar:** `get_events` for today, count files in `meetings/` matching today
- **Slack:** Search for your messages today

### 2. Write Daily Review

Save to `reviews/daily-review-YYYY-MM-DD.md`:

```
# Daily Review: [Day], [Date]

## By the numbers
- [N] tasks completed | [N] in progress | [N] awaiting review
- [N] meetings | [N] Slack threads contributed to

## What got done
[3-5 bullets grouped by theme, not a raw task list]

## Carry-forward
[Tasks still in doing/review that need attention tomorrow. Max 5.]
```

## Workflow: Weekly Review

### 1. Gather Week's Data

Same sources as daily but across the reporting week. Also:
- Count new files in `meetings/`, `research/reading-notes/`, `triages/`
- Fetch next week's events for preview (filter out declined)

### 2. Write Weekly Review

Save to `reviews/week-review-YYYY-MM-DD.md`:

```
# Week in Review: [Date range]

## By the numbers
- [N] tasks completed | [N] captured | [N] archived (won't-do) | [N] carried forward
- [N] meetings | [N] Slack threads | [artifact counts]

## What moved forward
[5-8 bullets grouped by theme. Focus on outcomes, not activity.]

## Wins
[Things to highlight upward. 2-4 bullets.]

## Risks
[Blockers, missed deadlines. Each with a proposed mitigation. 2-4 bullets.]

## Next week preview
[Calendar load per day + top 3-5 carry-forward tasks]
```

## Graceful Degradation

| Scenario | Behavior |
|----------|----------|
| Calendar unavailable | Skip meeting counts and next week preview |
| Crux unavailable | Hard stop - task data is essential |
| Slack unavailable | Skip Slack activity signals |

## Key Principles

- **Sharable output.** Weekly review should be directly sharable with your manager.
- **Honest numbers.** If a guardrail is missed, say so.
- **Outcomes over activity.** Group by theme, lead with impact.
