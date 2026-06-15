# Memory System

Claude Code's memory system gives the agent persistent context across conversations. Without it, every new session starts from zero - the agent doesn't know your role, your preferences, or what you've been working on.

## How It Works

Memory files live in the `memory/` directory as markdown files with frontmatter headers. The index file `MEMORY.md` is loaded automatically by Claude Code at session start. Each entry in `MEMORY.md` is a one-line summary that links to a detailed memory file.

Example `MEMORY.md` entry:

```
- [Your role and background](user_profile.md) - Sr. Engineer at Acme Corp, platform team lead
```

Claude Code reads `MEMORY.md` on every session start, which gives it enough context to behave consistently. The linked files provide deeper detail when the agent needs it.

## Memory Types

Organize your memory files by type:

- **user** - Who you are, your role, preferences, schedule, writing style
- **feedback** - Corrections and guidance from past sessions (e.g., "don't use em dashes," "always include links")
- **project** - Ongoing work context, product details, team structure
- **reference** - Pointers to external systems (issue tracker instance URLs, project keys, API endpoints)

## File Format

Each memory file uses this structure:

```markdown
---
name: user-profile
description: Role, background, and team context
metadata:
  type: user
---

# User Profile

- Role: Senior Engineer, Platform Team
- Company: Acme Corp
- Team: Infrastructure & Developer Experience
- Focus areas: Internal tooling, CI/CD, developer productivity
- Manager: Jane Smith
```

The frontmatter (between the `---` markers) tells Claude Code what the memory is about. The body contains the actual knowledge.

## Creating Memories

You can create memories in two ways:

1. **Manually** - Write a markdown file in `memory/` with the frontmatter format above, then add a one-line entry to `MEMORY.md`
2. **Through Claude Code** - Ask the agent to remember something. It will create the file and update the index.

## How Memories Persist

Memory files are regular files in your repo. They persist across conversations because:

1. Claude Code reads `MEMORY.md` at the start of every session
2. The linked files are available for the agent to read when it needs deeper context
3. Changes to memory files are committed to git along with everything else

Claude Code stores its memory path at `~/.claude/projects/<project-path>/memory`. The recommended setup is to symlink this to your repo's `memory/` directory so everything stays in one place:

```bash
mkdir -p ~/.claude/projects/-home-yourname-Projects-your-repo
ln -s ~/Projects/your-repo/memory ~/.claude/projects/-home-yourname-Projects-your-repo/memory
```

Replace the path segments with your actual project path. Claude Code encodes the path by replacing `/` with `-`.

## Getting Started

Start with two files. Example templates are included - copy them and fill in your details:

```bash
cp user_profile.example.md user_profile.md
cp user_writing_style.example.md user_writing_style.md
```

1. **`user_profile.md`** - Your role, team, company, focus areas, and key context the agent should always know
2. **`user_writing_style.md`** - How you want the agent to write (tone, formatting preferences, things to avoid)

Then add entries to `MEMORY.md`:

```
- [Your role and background](user_profile.md) - Your role, team, and focus areas
- [Writing style](user_writing_style.md) - Tone, formatting, things to avoid
```

These two files alone make a dramatic difference in output quality. Add more as you go - every time you correct the agent on something that should be permanent, that's a candidate for a feedback memory.

## Tips

- Keep memory files focused. One topic per file is better than one large file.
- Use the feedback type liberally. Every correction you make more than once should become a memory.
- Reference memories are great for things you'd otherwise have to re-explain every session (issue tracker project keys, API endpoints, team conventions).
- Review your memories periodically. Remove stale entries and update ones that have drifted.
