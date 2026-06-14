---
name: learn
description: Analyze user corrections from the conversation, extract generalizable rules, and persist them. Use after receiving corrections or at session end.
argument-hint: [optional: specific correction to codify]
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
---

# Learn from Corrections

Review the current conversation for corrections, extract generalizable rules, and persist them.

## Workflow

### 1. Identify Corrections

Look for:
- **Explicit corrections**: "No, don't do X" / "That's wrong, it should be Y"
- **Implicit corrections**: User rewrites output, ignores a suggestion, or asks again with more specificity
- **Positive confirmations**: "Yes, exactly like that" / acceptance of a non-obvious approach

### 2. Extract the Principle

For each correction:
- **Is it generalizable?** "Use bullet points not paragraphs" is. "Change this sentence" is not.
- **What's the scope?** All agent behavior, a specific skill, a specific tool?
- **Is there a "why"?** Rules with reasons are more useful than bare rules.

Skip one-time, task-specific corrections.

### 3. Route to the Right File

| Type | Target |
|------|--------|
| Global agent behavior | `CLAUDE.md` |
| User preferences | `memory/feedback_*.md` |
| Skill-specific | `.claude/skills/*/SKILL.md` |
| Domain knowledge | `{domain}/knowledge.md` |

### 4. Implement the Change

- **Memory files:** Follow the frontmatter format (`name`, `description`, `type: feedback`). Structure as: rule, then **Why:** and **How to apply:** lines. Update `memory/MEMORY.md` index.
- **CLAUDE.md:** Add to the relevant section, one line per rule.
- **Skills:** Add to the skill's Key Principles or update the workflow step.

Check existing files first - update rather than duplicate.

### 5. Verify and Summarize

Read back every modified file. Check frontmatter integrity and markdown validity.

Present a summary for each correction:

```
## Learned

### [Correction]
- **What was corrected:** [wrong behavior]
- **Principle:** [the rule]
- **Why:** [user's reasoning]
- **Updated:** [file path]
```

## Key Principles

- **Rules need reasons.** Always capture the why.
- **Update, don't duplicate.** Check existing files first.
- **Positive patterns matter.** Codify confirmed approaches, not just mistakes.
- **Scope tightly.** Skill-specific rules stay in skills, not CLAUDE.md.
