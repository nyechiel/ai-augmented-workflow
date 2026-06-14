# Disaster Recovery Procedure

Step-by-step guide to restore your full AI-augmented workflow on a new machine. This takes you from zero to a working system.

## What Gets Backed Up

| Asset | Backup method | Backup location |
|-------|---------------|-----------------|
| Workflow repo | Git commit + push | Your Git remote (GitHub, GitLab, etc.) |
| Crux code | Bundled in workflow repo | Your Git remote |
| App Dashboard | Bundled in workflow repo | Your Git remote |
| Crux task DB | sqlite3 snapshot | `backups/crux.db` (versioned in git) |
| Claude Code config | File copy | `backups/claude-config/` |
| Service definitions | File copy | `backups/services/` |
| MCP server forks | Git commit + push | GitHub (origin) |
| MCP secrets | Manual | Password manager (save once) |

The backup runs daily via a scheduled task (`scripts/backup.sh`). Logs go to `backups/backup.log`.

## Prerequisites

Before starting:

- [ ] SSH key registered with your Git hosting provider
- [ ] `mcp-secrets.env` from your password manager (Google OAuth tokens, Slack tokens, API keys)
- [ ] Claude Code subscription or API key

## Phase 1: Clone Repositories

### Main repos

```bash
mkdir -p ~/Projects
cd ~/Projects

# Replace with your actual repo URL
git clone git@github.com:YOUR_USERNAME/ai-augmented-workflow.git ai-augmented-workflow
```

Crux and App Dashboard are bundled in the workflow repo at `crux/` and `app-dashboard/`.

### MCP server forks

```bash
cd ~/Projects

git clone https://github.com/YOUR_USERNAME/google_workspace_mcp.git
git clone https://github.com/YOUR_USERNAME/slack-mcp-server.git
git clone https://github.com/YOUR_USERNAME/mcp-google-contacts-server.git
```

For each MCP fork, check out the branch with your local changes:

```bash
cd ~/Projects/google_workspace_mcp && git checkout your-branch
cd ~/Projects/slack-mcp-server && git checkout your-branch
# etc.
```

## Phase 2: Restore Crux

### Install Crux

```bash
cd ~/Projects/ai-augmented-workflow/crux
pip install -e .
```

This installs both the Crux web server and the MCP server (`crux-mcp`).

### Restore the task database

The latest DB snapshot is in the workflow repo at `backups/crux.db`.

```bash
mkdir -p ~/.crux
cp ~/Projects/ai-augmented-workflow/backups/crux.db ~/.crux/crux.db
```

### Verify

```bash
sqlite3 ~/.crux/crux.db "SELECT count(*) FROM tasks;"
crux-mcp --help
```

The first command should return your task count. The second should show CLI help.

## Phase 3: Restore Claude Code

### Install Claude Code

```bash
npm install -g @anthropic-ai/claude-code
```

### Restore configuration

```bash
mkdir -p ~/.claude
cp ~/Projects/ai-augmented-workflow/backups/claude-config/settings.json ~/.claude/settings.json
cp ~/Projects/ai-augmented-workflow/backups/claude-config/mcp-global.json ~/.claude/.mcp.json
cp ~/Projects/ai-augmented-workflow/backups/claude-config/credentials.json ~/.claude/.credentials.json
chmod 600 ~/.claude/.credentials.json
```

If `credentials.json` is not in the backup, authenticate manually:

```bash
claude login
```

### Set up memory symlink

Claude Code memory lives inside the workflow repo. The symlink makes Claude Code find it at its expected path.

**Linux / macOS:**

```bash
PROJECT_PATH="ai-augmented-workflow"  # adjust to match your setup
mkdir -p ~/.claude/projects/-home-$(whoami)-Projects-${PROJECT_PATH}
ln -s ~/Projects/${PROJECT_PATH}/memory ~/.claude/projects/-home-$(whoami)-Projects-${PROJECT_PATH}/memory
```

**Windows (PowerShell, run as Administrator):**

See `docs/SETUP.md` step 4.3 for the PowerShell equivalent.

Verify: start `claude` from your workflow directory and check that memory loads (the agent should reference your role, preferences, etc.).

### Restore project MCP config

The project-level `.mcp.json` is already in the workflow repo (tracked in git), so no action needed after cloning.

## Phase 4: Restore MCP Stack

### Install a container runtime

**Linux (Podman):**

```bash
# Fedora/RHEL
sudo dnf install -y podman podman-compose

# Ubuntu/Debian
sudo apt install -y podman python3-pip
pip install podman-compose
```

**macOS / Windows:**

Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) - it includes Docker Compose and works on both platforms. Alternatively, on macOS: `brew install podman podman-compose`.

### Restore secrets

Copy `mcp-secrets.env` from your password manager into the workflow repo root:

```bash
cp /path/to/saved/mcp-secrets.env ~/Projects/ai-augmented-workflow/mcp-secrets.env
chmod 600 ~/Projects/ai-augmented-workflow/mcp-secrets.env   # Linux/macOS only
```

This file contains Google OAuth refresh tokens, Slack tokens, and other API credentials. If you don't have it saved, you'll need to re-authenticate each service (see each server's README for OAuth setup instructions).

### Build and start the stack

```bash
cd ~/Projects/ai-augmented-workflow/local-mcp-stack
podman-compose up -d    # or: docker compose up -d
```

### Verify MCP proxy

```bash
curl -s http://localhost:9090/time/sse
```

Should return an SSE stream. If it hangs or errors, check container logs:

```bash
podman-compose logs    # or: docker compose logs
```

## Phase 5: Restore Autostart Services

Backed-up service definitions are in `backups/services/`. Restore them for your platform:

### Linux (systemd)

```bash
mkdir -p ~/.config/systemd/user
cp ~/Projects/ai-augmented-workflow/backups/services/*.service ~/.config/systemd/user/
cp ~/Projects/ai-augmented-workflow/backups/services/*.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now app-dashboard.service
systemctl --user enable --now workflow-backup.timer
loginctl enable-linger $(whoami)   # services survive logout
```

### macOS (launchd)

```bash
cp ~/Projects/ai-augmented-workflow/backups/services/*.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.app-dashboard.plist
launchctl load ~/Library/LaunchAgents/com.workflow-backup.plist
```

### Windows

Use Task Scheduler to recreate the App Dashboard and backup tasks. See `docs/SETUP.md` for details.

### Verify

- App Dashboard: open `http://localhost:9000` in a browser
- Backup timer: run `scripts/backup.sh` manually and check `backups/backup.log`

## Phase 6: Verify Everything

Run through this checklist to confirm the full stack is operational:

### Core workspace

- [ ] `cd ~/Projects/ai-augmented-workflow && claude` starts Claude Code
- [ ] Agent loads memory (mentions your role, preferences in responses)
- [ ] Skills are available (type `/` to see the list)

### MCP services

- [ ] Crux responds (create a test task in Claude Code)
- [ ] Google Workspace tools work (ask Claude to check your calendar)
- [ ] Slack tools work (ask Claude to check unreads)
- [ ] Google Contacts work (ask Claude to look up a colleague)
- [ ] Time tool works (ask Claude for current time)

### Infrastructure

- [ ] App Dashboard at `http://localhost:9000` shows all services green
- [ ] Backup is scheduled (check systemd timer, launchd, or Task Scheduler)
- [ ] Run backup manually: `~/Projects/ai-augmented-workflow/scripts/backup.sh`
- [ ] Check log: `tail ~/Projects/ai-augmented-workflow/backups/backup.log` shows success

### Git remotes

- [ ] `cd ~/Projects/ai-augmented-workflow && git push --dry-run` succeeds

## Recovery Time Estimate

| Phase | Estimated time |
|-------|---------------|
| Clone repos | 5 min |
| Restore Crux | 5 min |
| Restore Claude Code | 10 min |
| Restore MCP stack | 15-20 min |
| Restore autostart services | 5 min |
| Verification | 10 min |
| **Total** | **~50-55 min** |

This assumes all secrets are available in the password manager. If Google OAuth tokens need re-creation, add 15-20 minutes for the OAuth flow.

## What You'll Lose

Even with a perfect recovery, some things don't survive:

- **In-flight Claude Code sessions** - Any active conversation context is lost. Use the handoff mechanism before a planned migration.
- **Crux changes since last backup** - The DB snapshot is from the most recent backup run. Any tasks created or modified after the last backup are lost.
- **Unsaved repo changes** - Any uncommitted work since the last backup commit.
- **Browser state** - Saved passwords, bookmarks, and browser sessions are separate from this backup system.

## Keeping This Procedure Current

When you change the backup setup (add a new repo, new MCP server, new systemd service), update this file. The backup script handles _what_ gets backed up; this file handles _how to put it back together_.
