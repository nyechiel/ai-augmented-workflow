#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

# --- helpers ---

info()  { echo "[setup] $*"; }
skip()  { echo "[setup] $* (already exists, skipping)"; }
warn()  { echo "[setup] WARNING: $*"; }
fail()  { echo "[setup] ERROR: $*" >&2; exit 1; }

check_command() {
    if ! command -v "$1" &>/dev/null; then
        warn "$1 not found - $2"
        MISSING_PREREQS=1
    else
        info "$1 found: $(command -v "$1")"
    fi
}

# --- prerequisites ---

info "Checking prerequisites..."
MISSING_PREREQS=0

check_command python3 "Python 3.10+ is required (https://python.org)"
check_command node "Node.js 18+ is required for Claude Code (https://nodejs.org)"
check_command git "git is required (https://git-scm.com)"
check_command sqlite3 "sqlite3 is required for Crux database backups"

COMPOSE_CMD=""
if command -v podman-compose &>/dev/null; then
    COMPOSE_CMD="podman-compose"
    info "Container runtime: podman-compose"
elif command -v docker &>/dev/null && docker compose version &>/dev/null; then
    COMPOSE_CMD="docker compose"
    info "Container runtime: docker compose"
else
    warn "No container runtime found - install Docker Desktop or Podman + podman-compose"
    MISSING_PREREQS=1
fi

if [ "$MISSING_PREREQS" -eq 1 ]; then
    warn "Some prerequisites are missing. Install them and re-run this script."
    warn "Continuing with remaining steps..."
    echo ""
fi

# --- step 1: install Crux ---

info ""
info "=== Installing Crux (task board) ==="

VENV_DIR="$HOME/.venvs/crux"
if ! command -v python3 &>/dev/null; then
    warn "Skipping Crux install (python3 not found)"
elif [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/crux-mcp" ]; then
    skip "Crux virtualenv at $VENV_DIR"
else
    info "Creating virtualenv at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
    info "Installing Crux..."
    "$VENV_DIR/bin/pip" install -e "$REPO_DIR/crux"
    info "Crux installed. CLI: $VENV_DIR/bin/crux, MCP: $VENV_DIR/bin/crux-mcp"
fi

# --- step 2: install App Dashboard ---

info ""
info "=== Installing App Dashboard ==="

DASH_VENV="$HOME/.venvs/app-dashboard"
if ! command -v python3 &>/dev/null; then
    warn "Skipping App Dashboard install (python3 not found)"
elif [ -f "$DASH_VENV/bin/python" ] && "$DASH_VENV/bin/python" -c "import fastapi" 2>/dev/null; then
    skip "App Dashboard virtualenv at $DASH_VENV"
else
    info "Creating virtualenv at $DASH_VENV..."
    python3 -m venv "$DASH_VENV"
    info "Installing dependencies..."
    "$DASH_VENV/bin/pip" install -r "$REPO_DIR/app-dashboard/requirements.txt"
    info "App Dashboard installed."
fi

# --- step 3: copy example files ---

info ""
info "=== Copying example files ==="

copy_example() {
    local src="$1" dst="$2"
    if [ -f "$dst" ]; then
        skip "$dst"
    else
        cp "$src" "$dst"
        info "Created $dst"
    fi
}

copy_example ".env.example" "mcp-secrets.env"
copy_example "CLAUDE.md.example" "CLAUDE.md"
copy_example ".mcp.json.example" ".mcp.json"
copy_example "app-dashboard/apps.json.example" "app-dashboard/apps.json"

# restrict secrets file
if [ -f "mcp-secrets.env" ]; then
    chmod 600 mcp-secrets.env
fi

# --- step 4: fill in username in apps.json ---

info ""
info "=== Configuring paths ==="

CURRENT_USER="$(whoami)"
if grep -q "YOUR_USERNAME" "app-dashboard/apps.json" 2>/dev/null; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/YOUR_USERNAME/$CURRENT_USER/g" "app-dashboard/apps.json"
    else
        sed -i "s/YOUR_USERNAME/$CURRENT_USER/g" "app-dashboard/apps.json"
    fi
    info "Replaced YOUR_USERNAME with $CURRENT_USER in app-dashboard/apps.json"
else
    skip "app-dashboard/apps.json already configured"
fi

# --- step 5: skills symlink ---

info ""
info "=== Setting up skills symlink ==="

mkdir -p .claude
if [ -L ".claude/skills" ]; then
    skip ".claude/skills symlink"
elif [ -d ".claude/skills" ]; then
    skip ".claude/skills directory exists"
else
    ln -s ../skills .claude/skills
    info "Created .claude/skills -> ../skills"
fi

# --- step 6: memory symlink ---

info ""
info "=== Setting up memory symlink ==="

PROJECT_PATH="$(pwd | sed 's|/|-|g; s|^-||')"
MEMORY_TARGET="$HOME/.claude/projects/-${PROJECT_PATH}/memory"

if [ -L "$MEMORY_TARGET" ]; then
    skip "Memory symlink at $MEMORY_TARGET"
else
    mkdir -p "$(dirname "$MEMORY_TARGET")"
    ln -s "$(pwd)/memory" "$MEMORY_TARGET"
    info "Created memory symlink at $MEMORY_TARGET"
fi

# --- step 7: add venv bins to PATH reminder ---

info ""
info "=== Setup complete ==="
info ""
info "Add the virtualenv bins to your PATH so Claude Code can find them:"
info "  export PATH=\"$HOME/.venvs/crux/bin:$HOME/.venvs/app-dashboard/bin:\$PATH\""
info ""
info "Or add that line to your ~/.bashrc or ~/.zshrc."
info ""
info "--- What's left (manual steps) ---"
info ""
info "1. Fork and clone the MCP servers you need:"
info "   - Google Workspace: https://github.com/nyechiel/google_workspace_mcp (branch: patches-for-upstream)"
info "   - Slack: https://github.com/nyechiel/slack-mcp-server (branch: feat/activity-and-saved-tools)"
info "   - Google Contacts: https://github.com/nyechiel/mcp-google-contacts-server"
info ""
info "2. Configure credentials in mcp-secrets.env:"
info "   - Google OAuth (client ID, secret, refresh token)"
info "   - Slack browser tokens (xoxc/xoxd)"
info "   - See docs/SETUP.md for detailed instructions"
info ""
info "3. Start the MCP stack:"
info "   cd local-mcp-stack && ${COMPOSE_CMD:-docker compose} up -d"
info ""
info "4. Customize CLAUDE.md with your rules, integrations, and context"
info ""
info "5. Start Claude Code and try a skill:"
info "   cd $REPO_DIR && claude"
info "   Type / to see available skills"
info ""
info "See docs/SETUP.md for the full guide and docs/CUSTOMIZATION.md for role-specific setup."
