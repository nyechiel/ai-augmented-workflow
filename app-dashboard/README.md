# App Dashboard

A lightweight web UI for managing local services - start, stop, restart, monitor health, and view logs from a single page.

## The Problem

Running an AI-augmented workflow means juggling multiple local services: MCP servers behind a proxy, a task board, maybe a few side projects. After a reboot, you need to remember which ones to start. When something breaks, you're checking container logs, process status, and ports across multiple terminals.

App Dashboard puts all of that in one place.

## Features

- **Service lifecycle** - Start, stop, restart individual services or entire Compose stacks
- **Health monitoring** - Status dots (green/yellow/red) per service, auto-refreshed
- **Log viewer** - Tail logs for any service without leaving the browser
- **Autostart** - Toggle which services start on boot
- **Compose support** - Manage Podman/Docker Compose stacks as a single app with per-container status
- **Backup status** - See when the last backup ran and what's coming next

## Setup

### 1. Install dependencies

```bash
cd app-dashboard
pip install -r requirements.txt    # use a virtualenv if your OS requires it (see crux/README.md)
```

### 2. Configure your apps

```bash
cp apps.json.example apps.json
```

Edit `apps.json` to define your services. Each app has an ID, name, and one or more services:

```json
{
  "id": "crux",
  "name": "Crux",
  "description": "Task management with kanban board",
  "url": "http://localhost:8487",
  "autostart": true,
  "services": [
    {
      "name": "server",
      "directory": "/home/YOUR_USERNAME/Projects/ai-augmented-workflow/crux",
      "command": "crux web --port 8487",
      "port": 8487
    }
  ]
}
```

For Compose stacks, use `type: "compose"`:

```json
{
  "id": "mcp-stack",
  "name": "MCP Stack",
  "type": "compose",
  "compose": {
    "file": "/home/YOUR_USERNAME/Projects/ai-augmented-workflow/local-mcp-stack/docker-compose.yml",
    "env_file": "/home/YOUR_USERNAME/Projects/ai-augmented-workflow/mcp-secrets.env"
  },
  "services": [
    {"name": "google-workspace", "port": 8001},
    {"name": "slack", "port": 13070}
  ]
}
```

> **Note:** Use absolute paths in `apps.json` - tilde (`~`) and environment variables are not expanded by the Python process.

### 3. Run it

```bash
python server.py
```

Open `http://localhost:9000` in your browser.

### 4. Run on startup (recommended)

The dashboard manages autostart for your other services, so it should start automatically on boot.

**Linux (systemd):**

Create `~/.config/systemd/user/app-dashboard.service`:

```ini
[Unit]
Description=App Dashboard
After=default.target

[Service]
ExecStart=/usr/bin/python3 %h/Projects/ai-augmented-workflow/app-dashboard/server.py
WorkingDirectory=%h/Projects/ai-augmented-workflow/app-dashboard
Restart=on-failure
RestartSec=5
Environment=PATH=%h/.local/bin:/usr/local/bin:/usr/bin

[Install]
WantedBy=default.target
```

Enable it:

```bash
systemctl --user daemon-reload
systemctl --user enable --now app-dashboard.service
loginctl enable-linger $(whoami)
```

The `enable-linger` command ensures the service survives logout.

**macOS (launchd):**

Create `~/Library/LaunchAgents/com.app-dashboard.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.app-dashboard</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>server.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/YOUR_USERNAME/Projects/ai-augmented-workflow/app-dashboard</string>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
</dict>
</plist>
```

Load it:

```bash
launchctl load ~/Library/LaunchAgents/com.app-dashboard.plist
```

**Windows:**

Add a shortcut to `shell:startup` that runs `python server.py` from the `app-dashboard` directory, or create a Task Scheduler task that runs at logon.

After a reboot, the dashboard starts automatically and launches any apps with `autostart: true`.

## Configuration

### Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `BACKUP_SCRIPT` | *(relative to app-dashboard)* `../scripts/backup.sh` | Path to the backup script |
| `BACKUP_LOG` | *(relative to app-dashboard)* `../backups/backup.log` | Path to the backup log |
| `BACKUP_REPOS` | *(see below)* | JSON array of repos to show backup status for |

`BACKUP_REPOS` is a JSON array of objects with `name`, `path`, and `remote` fields. Override via environment variable if the defaults don't match your setup.

### Backup integration

The dashboard shows backup status (last run, next scheduled run, per-repo git status) by reading the backup log and checking the scheduled task. On Linux it reads the systemd timer (`workflow-backup.timer`); on macOS/Windows the "next run" display won't work but backup status and git info still show correctly.

### Platform notes

The dashboard uses `fcntl` for file locking, which is available on Linux and macOS. On Windows, run it inside WSL2 - native Windows is not supported.

## Security

App Dashboard binds to `127.0.0.1` only and has no authentication. It can start/stop processes and execute commands defined in `apps.json`. Never expose it to the network - it should only be accessible from your local machine.

## License

MIT
