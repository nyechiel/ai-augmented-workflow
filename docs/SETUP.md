# Setup Guide

Step-by-step guide to building your own AI-augmented workflow. By the end, you'll have Claude Code connected to your email, calendar, chat, task board, and project tracker - all running locally.

## Prerequisites

- [Node.js](https://nodejs.org/) 18+ (required by Claude Code)
- [Claude Code](https://claude.ai/claude-code) installed (`npm install -g @anthropic-ai/claude-code`)
- A container runtime: [Docker Desktop](https://www.docker.com/products/docker-desktop/) (macOS/Windows) or [Podman](https://podman.io/) + podman-compose (Linux)
- Git
- Python 3.10+
- SQLite (`sqlite3` CLI)

> **Note:** This guide shows Linux commands. On macOS, the same commands work in Terminal. On Windows, use WSL2, Git Bash, or PowerShell - see platform-specific notes where they differ.

## Quick setup

The setup script automates steps 1-4 below (Crux, App Dashboard, config files, symlinks):

```bash
git clone https://github.com/YOUR_USERNAME/ai-augmented-workflow.git ~/Projects/ai-augmented-workflow
cd ~/Projects/ai-augmented-workflow
./scripts/setup.sh        # Linux/macOS/WSL2
# or: .\scripts\setup.ps1  # Windows PowerShell
```

Then skip to [step 3 (MCP stack)](#3-set-up-the-mcp-stack) for the manual parts. Or follow the full guide below for a step-by-step walkthrough.

## 1. Clone This Repo

```bash
git clone https://github.com/YOUR_USERNAME/ai-augmented-workflow.git ~/Projects/ai-augmented-workflow
cd ~/Projects/ai-augmented-workflow
```

## 2. Set Up the Task Board (Crux)

Crux is a lightweight Kanban task board with an MCP server. It's how Claude Code tracks tasks, action items, and work in progress.

```bash
cd ~/Projects/ai-augmented-workflow/crux

# Recommended: use a virtualenv (required on Fedora 39+, Ubuntu 23.04+, and other distros with PEP 668)
python3 -m venv ~/.venvs/crux
source ~/.venvs/crux/bin/activate

pip install -e .
```

Verify the install:

```bash
crux-mcp --help
```

This should print CLI help, confirming both the web server and the MCP server are installed.

Add the Crux virtualenv to your PATH so Claude Code can find the MCP server:

```bash
export PATH="$HOME/.venvs/crux/bin:$PATH"
```

Add this line to your `~/.bashrc` or `~/.zshrc` to make it permanent.

## 3. Set Up the MCP Stack

The MCP stack connects Claude Code to your external tools (email, calendar, chat, etc.) via the Model Context Protocol. Each tool runs as a containerized MCP server, with a proxy gateway in front.

### 3.1 Clone the MCP servers

Clone the MCP server repos you need. These are forks with patches needed for running in containers (auth flows, additional tools, startup fixes). Upstream PRs are pending - once merged, you can switch to the upstream repos directly.

- **Google Workspace** (Gmail, Calendar, Drive, Docs, Sheets, Slides): [https://github.com/nyechiel/google_workspace_mcp](https://github.com/nyechiel/google_workspace_mcp)
- **Slack**: [https://github.com/nyechiel/slack-mcp-server](https://github.com/nyechiel/slack-mcp-server)
- **Google Contacts** (directory lookup): [https://github.com/nyechiel/mcp-google-contacts-server](https://github.com/nyechiel/mcp-google-contacts-server)

The **MCP Proxy** ([TBXark/mcp-proxy](https://github.com/TBXark/mcp-proxy)) runs as a pre-built Docker image - no fork needed.

Clone each one locally:

```bash
cd ~/Projects
git clone -b patches-for-upstream https://github.com/nyechiel/google_workspace_mcp.git
git clone -b feat/activity-and-saved-tools https://github.com/nyechiel/slack-mcp-server.git
git clone https://github.com/nyechiel/mcp-google-contacts-server.git
```

Copy the custom Dockerfile for Google Contacts into your clone:

```bash
cp ~/Projects/ai-augmented-workflow/local-mcp-stack/Dockerfile.google-contacts \
   ~/Projects/mcp-google-contacts-server/Dockerfile
```

### 3.2 Configure secrets

```bash
cd ~/Projects/ai-augmented-workflow
cp .env.example mcp-secrets.env
chmod 600 mcp-secrets.env   # Linux/macOS only - restricts file to owner
```

Edit `mcp-secrets.env` and fill in your credentials:

- **Google OAuth** - You'll need a GCP project with the Gmail, Calendar, Drive, Docs, Sheets, Slides, and Contacts APIs enabled, plus an OAuth consent screen. Create an OAuth 2.0 Client ID (Desktop app), then use the [OAuth Playground](https://developers.google.com/oauthplayground/) or the GWS MCP server's built-in auth flow to obtain a refresh token. This is the most involved step - see the [google_workspace_mcp README](https://github.com/nyechiel/google_workspace_mcp) for a walkthrough.
- **Slack** - Browser session tokens (xoxc/xoxd), not bot tokens. Open Slack in your browser, open DevTools (F12), go to Application > Cookies, and copy the `d` cookie value (xoxd token). For the xoxc token, search network requests for `xoxc-`. See the [slack-mcp-server README](https://github.com/nyechiel/slack-mcp-server#authentication) for details.
- Any other API keys for your MCP servers

### 3.3 Start the stack

Create credential directories (containers need these mount points to exist):

```bash
mkdir -p ~/.google_workspace_mcp
mkdir -p ~/.config/google-contacts-mcp
```

Then start the stack:

```bash
cd ~/Projects/ai-augmented-workflow/local-mcp-stack
podman-compose up -d    # or: docker compose up -d
```

> **Docker users:** The `docker-compose.yml` uses Podman-specific volume flags (`:Z,U`). If you're using Docker, edit the file and remove `:Z,U` from the two volume mounts that have them, or the containers will fail to start.

### 3.4 Verify

```bash
curl -s http://localhost:9090/time/sse
```

You should see SSE events streaming. Press Ctrl+C to stop - seeing any events means it's working. If it hangs or errors, check logs:

```bash
podman-compose logs    # or: docker compose logs
```

## 4. Configure Claude Code

### 4.1 MCP connections

```bash
cd ~/Projects/ai-augmented-workflow
cp .mcp.json.example .mcp.json
```

Edit `.mcp.json` to point to your MCP servers. The example file includes entries for all supported servers.

### 4.2 Project instructions and skills

```bash
cp CLAUDE.md.example CLAUDE.md

# Create the skills symlink so Claude Code discovers your skills
mkdir -p .claude
ln -s ../skills .claude/skills
```

Edit `CLAUDE.md` to customize:

- Your protocol rules (what the agent should never do)
- Your repo structure
- Your MCP integrations and Cloud IDs
- Your skills list
- Key context (email, account IDs, etc.)

### 4.3 Memory symlink

Set up the memory symlink so Claude Code finds your memory files:

**Linux / macOS:**

```bash
PROJECT_PATH=$(pwd | sed 's|/|-|g; s|^-||')
mkdir -p ~/.claude/projects/-${PROJECT_PATH}
ln -s $(pwd)/memory ~/.claude/projects/-${PROJECT_PATH}/memory
```

**Windows (PowerShell, run as Administrator):**

```powershell
$projectPath = (Get-Location).Path -replace '[\\:]', '-' -replace '^-', ''
$target = "$env:USERPROFILE\.claude\projects\-$projectPath\memory"
New-Item -ItemType Directory -Path (Split-Path $target) -Force
New-Item -ItemType SymbolicLink -Path $target -Target "$(Get-Location)\memory"
```

## 5. Set Up the App Dashboard (Optional)

The App Dashboard gives you a web UI to manage all your local services. See `app-dashboard/README.md` for details.

```bash
cd ~/Projects/ai-augmented-workflow/app-dashboard
pip install -r requirements.txt
```

To start the dashboard automatically on boot:

**Linux (systemd):**

```bash
mkdir -p ~/.config/systemd/user
# See app-dashboard/README.md for the service file template
systemctl --user daemon-reload
systemctl --user enable --now app-dashboard.service
loginctl enable-linger $(whoami)
```

**macOS (launchd):**

Create `~/Library/LaunchAgents/com.app-dashboard.plist` - see `app-dashboard/README.md` for the plist template. Then:

```bash
launchctl load ~/Library/LaunchAgents/com.app-dashboard.plist
```

**Windows:**

Add a shortcut to `shell:startup` that runs `app-dashboard`, or create a Task Scheduler task that runs at logon.

## 6. Set Up Backup (Optional)

The backup script snapshots your task database, copies Claude Code config, and commits everything to git.

```bash
# Customize the paths at the top of backup.sh
chmod +x scripts/backup.sh
```

Schedule it to run daily:

**Linux (systemd timer):**

```bash
cat > ~/.config/systemd/user/workflow-backup.service << 'EOF'
[Unit]
Description=Workflow backup

[Service]
Type=oneshot
ExecStart=%h/Projects/ai-augmented-workflow/scripts/backup.sh
EOF

cat > ~/.config/systemd/user/workflow-backup.timer << 'EOF'
[Unit]
Description=Daily workflow backup

[Timer]
OnCalendar=*-*-* 15:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now workflow-backup.timer
```

**macOS (launchd):**

```bash
cat > ~/Library/LaunchAgents/com.workflow-backup.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.workflow-backup</string>
    <key>ProgramArguments</key><array><string>/bin/bash</string><string>-c</string><string>$HOME/Projects/ai-augmented-workflow/scripts/backup.sh</string></array>
    <key>StartCalendarInterval</key><dict><key>Hour</key><integer>15</integer><key>Minute</key><integer>0</integer></dict>
</dict>
</plist>
EOF
launchctl load ~/Library/LaunchAgents/com.workflow-backup.plist
```

**Windows (Task Scheduler):**

Open Task Scheduler and create a task that runs `bash scripts/backup.sh` daily (requires WSL2 or Git Bash).

## 7. Verify Everything

Start Claude Code from your project directory:

```bash
cd ~/Projects/ai-augmented-workflow
claude
```

Run through this checklist:

- [ ] Agent loads memory (references your role and preferences)
- [ ] Skills are available (type `/` to see the list)
- [ ] Crux works (ask Claude to create a test task)
- [ ] Google Workspace works (ask Claude to check your calendar)
- [ ] Slack works (ask Claude to check unreads)
- [ ] Time tool works (ask Claude for the current time)

If any tool fails, check:

1. Is the container running? (`podman ps` or `docker ps`)
2. Is the proxy up? (`curl -s http://localhost:9090/time/sse`)
3. Are credentials correct? (check `mcp-secrets.env`)
4. Check container logs: `podman-compose logs <service-name>` (or `docker compose logs <service-name>`)
