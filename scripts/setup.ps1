# AI-Augmented Workflow - Setup Script (Windows PowerShell)
# Run from the repo root: .\scripts\setup.ps1
# Note: Memory symlink requires Administrator privileges

$ErrorActionPreference = "Stop"
$RepoDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $RepoDir

function Info($msg) { Write-Host "[setup] $msg" }
function Skip($msg) { Write-Host "[setup] $msg (already exists, skipping)" }
function Warn($msg) { Write-Host "[setup] WARNING: $msg" -ForegroundColor Yellow }
function Fail($msg) { Write-Host "[setup] ERROR: $msg" -ForegroundColor Red; exit 1 }

# --- prerequisites ---

Info "Checking prerequisites..."
$missing = 0

foreach ($cmd in @("python", "node", "git", "sqlite3")) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        Info "$cmd found: $((Get-Command $cmd).Source)"
    } else {
        Warn "$cmd not found"
        $missing = 1
    }
}

if (Get-Command docker -ErrorAction SilentlyContinue) {
    Info "Container runtime: docker"
} else {
    Warn "Docker not found - install Docker Desktop (https://docker.com/products/docker-desktop/)"
    $missing = 1
}

if ($missing -eq 1) {
    Warn "Some prerequisites are missing. Install them and re-run this script."
    Warn "Continuing with remaining steps..."
    Write-Host ""
}

# --- step 1: install Crux ---

Info ""
Info "=== Installing Crux (task board) ==="

$VenvDir = "$env:USERPROFILE\.venvs\crux"
if ((Test-Path "$VenvDir\Scripts\crux-mcp.exe") -or (Test-Path "$VenvDir\Scripts\crux-mcp")) {
    Skip "Crux virtualenv at $VenvDir"
} else {
    Info "Creating virtualenv at $VenvDir..."
    python -m venv $VenvDir
    Info "Installing Crux..."
    & "$VenvDir\Scripts\pip" install -e "$RepoDir\crux"
    Info "Crux installed."
}

# --- step 2: install App Dashboard ---

Info ""
Info "=== Installing App Dashboard ==="

$DashVenv = "$env:USERPROFILE\.venvs\app-dashboard"
$dashCheck = $false
if (Test-Path "$DashVenv\Scripts\python.exe") {
    try {
        & "$DashVenv\Scripts\python" -c "import fastapi" 2>$null
        $dashCheck = $true
    } catch {}
}

if ($dashCheck) {
    Skip "App Dashboard virtualenv at $DashVenv"
} else {
    Info "Creating virtualenv at $DashVenv..."
    python -m venv $DashVenv
    Info "Installing dependencies..."
    & "$DashVenv\Scripts\pip" install -r "$RepoDir\app-dashboard\requirements.txt"
    Info "App Dashboard installed."
}

# --- step 3: copy example files ---

Info ""
Info "=== Copying example files ==="

function Copy-Example($src, $dst) {
    if (Test-Path $dst) {
        Skip $dst
    } else {
        Copy-Item $src $dst
        Info "Created $dst"
    }
}

Copy-Example ".env.example" "mcp-secrets.env"
Copy-Example "CLAUDE.md.example" "CLAUDE.md"
Copy-Example ".mcp.json.example" ".mcp.json"
Copy-Example "app-dashboard\apps.json.example" "app-dashboard\apps.json"

# --- step 4: fill in username in apps.json ---

Info ""
Info "=== Configuring paths ==="

$appsJson = "app-dashboard\apps.json"
if ((Test-Path $appsJson) -and (Select-String -Path $appsJson -Pattern "YOUR_USERNAME" -Quiet)) {
    $content = Get-Content $appsJson -Raw
    $content = $content -replace "YOUR_USERNAME", $env:USERNAME
    Set-Content $appsJson $content
    Info "Replaced YOUR_USERNAME with $env:USERNAME in $appsJson"
} else {
    Skip "$appsJson already configured"
}

# --- step 5: skills symlink ---

Info ""
Info "=== Setting up skills symlink ==="

if (-not (Test-Path ".claude")) {
    New-Item -ItemType Directory -Path ".claude" -Force | Out-Null
}

if (Test-Path ".claude\skills") {
    Skip ".claude\skills"
} else {
    New-Item -ItemType SymbolicLink -Path ".claude\skills" -Target "$RepoDir\skills" | Out-Null
    Info "Created .claude\skills -> skills"
}

# --- step 6: memory symlink ---

Info ""
Info "=== Setting up memory symlink ==="

$projectPath = (Get-Location).Path -replace '[\\:]', '-' -replace '^-', ''
$memoryTarget = "$env:USERPROFILE\.claude\projects\-$projectPath\memory"

if (Test-Path $memoryTarget) {
    Skip "Memory symlink at $memoryTarget"
} else {
    $parentDir = Split-Path $memoryTarget
    New-Item -ItemType Directory -Path $parentDir -Force | Out-Null
    try {
        New-Item -ItemType SymbolicLink -Path $memoryTarget -Target "$RepoDir\memory" | Out-Null
        Info "Created memory symlink at $memoryTarget"
    } catch {
        Warn "Failed to create memory symlink. Run this script as Administrator, or create it manually:"
        Warn "  New-Item -ItemType SymbolicLink -Path '$memoryTarget' -Target '$RepoDir\memory'"
    }
}

# --- step 7: PATH reminder ---

Info ""
Info "=== Setup complete ==="
Info ""
Info "Add the virtualenv bins to your PATH so Claude Code can find them:"
Info "  `$env:PATH = `"$env:USERPROFILE\.venvs\crux\Scripts;$env:USERPROFILE\.venvs\app-dashboard\Scripts;`$env:PATH`""
Info ""
Info "Or add it permanently via System Properties > Environment Variables."
Info ""
Info "--- What's left (manual steps) ---"
Info ""
Info "1. Fork and clone the MCP servers you need:"
Info "   - Google Workspace: https://github.com/nyechiel/google_workspace_mcp (branch: patches-for-upstream)"
Info "   - Slack: https://github.com/nyechiel/slack-mcp-server (branch: feat/activity-and-saved-tools)"
Info "   - Google Contacts: https://github.com/nyechiel/mcp-google-contacts-server"
Info ""
Info "2. Configure credentials in mcp-secrets.env:"
Info "   - Google OAuth (client ID, secret, refresh token)"
Info "   - Slack browser tokens (xoxc/xoxd)"
Info "   - See docs/SETUP.md for detailed instructions"
Info ""
Info "3. Start the MCP stack:"
Info "   cd local-mcp-stack; docker compose up -d"
Info ""
Info "4. Customize CLAUDE.md with your rules, integrations, and context"
Info ""
Info "5. Start Claude Code and try a skill:"
Info "   cd $RepoDir; claude"
Info "   Type / to see available skills"
Info ""
Info "See docs/SETUP.md for the full guide and docs/CUSTOMIZATION.md for role-specific setup."
