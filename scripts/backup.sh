#!/bin/bash
# Workflow daily backup - runs via systemd timer
# Snapshots Crux DB, copies external configs, commits + pushes repos
#
# Customize the paths below to match your setup.
set -euo pipefail

# --- CUSTOMIZE THIS PATH ---
WORKFLOW_REPO="$HOME/Projects/ai-augmented-workflow"  # Your main workflow repo
# --- END CUSTOMIZATION ---

LOG="$WORKFLOW_REPO/backups/backup.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M')] $1" >> "$LOG"; }

log "--- Backup started ---"

# 1. Snapshot Crux DB (consistent copy even while Crux is running)
mkdir -p "$WORKFLOW_REPO/backups"
if command -v sqlite3 &>/dev/null && [ -f "$HOME/.crux/crux.db" ]; then
    sqlite3 "$HOME/.crux/crux.db" ".backup $WORKFLOW_REPO/backups/crux.db"
    log "Crux DB snapshot done"
else
    log "Crux DB snapshot skipped (sqlite3 or DB not found)"
fi

# 2. Copy Claude Code config
# WARNING: credentials.json contains auth tokens. backups/ is gitignored but
# never remove that gitignore entry or force-add this directory.
mkdir -p "$WORKFLOW_REPO/backups/claude-config"
cp "$HOME/.claude/settings.json" "$WORKFLOW_REPO/backups/claude-config/" 2>/dev/null || true
cp "$HOME/.claude/.mcp.json" "$WORKFLOW_REPO/backups/claude-config/mcp-global.json" 2>/dev/null || true
cp "$HOME/.claude/.credentials.json" "$WORKFLOW_REPO/backups/claude-config/credentials.json" 2>/dev/null || true

# 3. Copy service definitions (Linux systemd / macOS launchd)
mkdir -p "$WORKFLOW_REPO/backups/services"
if [ -d "$HOME/.config/systemd/user" ]; then
    for f in "$HOME/.config/systemd/user/"*.service "$HOME/.config/systemd/user/"*.timer; do
        [ -f "$f" ] && cp "$f" "$WORKFLOW_REPO/backups/services/" 2>/dev/null || true
    done
fi
if [ -d "$HOME/Library/LaunchAgents" ]; then
    for f in "$HOME/Library/LaunchAgents/com.workflow"*.plist "$HOME/Library/LaunchAgents/com.app-dashboard"*.plist; do
        [ -f "$f" ] && cp "$f" "$WORKFLOW_REPO/backups/services/" 2>/dev/null || true
    done
fi

# 4. Commit + push each repo
backup_repo() {
    local repo_path="$1"
    local repo_name="$2"

    if [ ! -d "$repo_path/.git" ]; then
        log "$repo_name: not a git repo, skipping"
        return
    fi

    cd "$repo_path"

    if ! git diff --quiet HEAD 2>/dev/null || [ -n "$(git ls-files --others --exclude-standard 2>/dev/null)" ]; then
        git add -A
        git commit -m "backup: $(date '+%Y-%m-%d')" 2>/dev/null || true
        log "$repo_name: committed"
    else
        log "$repo_name: no changes"
    fi

    if git remote get-url origin &>/dev/null; then
        if timeout 30 git push --quiet 2>/dev/null; then
            log "$repo_name: pushed"
        else
            log "$repo_name: push failed"
        fi
    else
        log "$repo_name: no remote configured, skipping push"
    fi
}

backup_repo "$WORKFLOW_REPO" "workflow"

# Optional: add more repos here (e.g. MCP server forks)
# backup_repo "$HOME/Projects/your-mcp-fork" "mcp-fork"

log "--- Backup complete ---"
