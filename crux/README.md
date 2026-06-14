# Crux

Personal task manager with a Kanban web UI, CLI, and MCP server.

## Quick Start

Create a virtualenv (recommended, required on Fedora 39+ / Ubuntu 23.04+):

**Linux / macOS:**

```bash
python3 -m venv ~/.venvs/crux && source ~/.venvs/crux/bin/activate
```

**Windows (PowerShell):**

```powershell
python -m venv $env:USERPROFILE\.venvs\crux
& $env:USERPROFILE\.venvs\crux\Scripts\Activate.ps1
```

Then install and run:

```bash
pip install -e .
crux add "My first task"       # CLI
crux web                       # Web UI at http://localhost:8487
crux-mcp                       # MCP server for Claude
```

## Architecture

- **CLI** (`crux`) - Click-based commands for adding, listing, editing, and moving tasks
- **Web UI** - FastAPI backend + single-file Kanban board frontend (HTML/CSS/JS)
- **MCP Server** (`crux-mcp`) - 12 tools for AI agents: task CRUD, comments, labels, search
- **Database** - SQLite at `~/.crux/crux.db` via SQLAlchemy

```
src/crux/
  cli/commands.py       # CLI commands
  web/server.py         # FastAPI REST API
  web/static/index.html # Kanban board UI
  db/models.py          # SQLAlchemy models (Task, Label, Comment)
  mcp_server.py         # MCP server
```

## Web UI Features

- **Kanban board** with 6 columns: Todo, Doing, Review, Blocked, Done, Archived
- **Drag-and-drop** reordering within and across columns
- **Task modal** - GitHub-style two-column layout with description, checklist, comments, and metadata sidebar
- **Labels** - many-to-many, click to filter, autocomplete input
- **Priority** - high/medium/low with colored badges
- **Estimates** - T-shirt sizes (XS-XL), auto-suggested from task content
- **Checklist** - inline items with progress counter
- **Due dates** - overdue/today visual indicators
- **Search** - real-time keyword search with highlighting
- **Today and Deep Work** - focus flags with dedicated strips
- **Rich text** - bold, italic, code formatting in descriptions

## CLI Commands

```bash
crux add "Title" --desc "..." --due 2026-06-01 --priority high --label bug
crux list [--status todo] [--label bug] [--priority high]
crux start TASK_ID         # move to doing
crux done TASK_ID          # move to done
crux review TASK_ID        # move to review
crux block TASK_ID         # move to blocked
crux archive TASK_ID       # move to archived
crux edit TASK_ID --title "New title"
crux rm TASK_ID
crux labels
crux web [--port PORT]         # Web UI (default port: 8487)
```

## MCP Server

The MCP server exposes task management tools for AI assistants. Configure in `.mcp.json`:

```json
{
  "mcpServers": {
    "crux": {
      "command": "crux-mcp"
    }
  }
}
```

Tools: `list_tasks`, `add_task`, `edit_task`, `move_task`, `delete_task`, `get_task`, `search_tasks`, `assign_task`, `add_comment`, `edit_comment`, `delete_comment`, `list_labels`

## Configuration

Database location:
- **Linux / macOS:** `~/.crux/crux.db`
- **Windows:** `%USERPROFILE%\.crux\crux.db`

## Security

Crux binds to `127.0.0.1` only and has no authentication. It stores tasks in a local SQLite database at `~/.crux/crux.db`. Never expose the web server to the network - it should only be accessible from your local machine.

## Dependencies

- Python 3.10+
- click, fastapi, uvicorn, sqlalchemy, mcp
