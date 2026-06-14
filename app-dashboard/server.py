import fcntl
import json
import os
import shlex
import signal
import socket
import subprocess
import tempfile
import time
from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "apps.json"
LOGS_DIR = BASE_DIR / "logs"

processes: dict[str, dict[str, subprocess.Popen]] = {}
LOCK_PATH = BASE_DIR / ".apps.lock"

BACKUP_SCRIPT = Path(os.environ.get(
    "BACKUP_SCRIPT", str(BASE_DIR.parent / "scripts/backup.sh")))
BACKUP_LOG = Path(os.environ.get(
    "BACKUP_LOG", str(BASE_DIR.parent / "backups/backup.log")))
BACKUP_REPOS = json.loads(os.environ.get("BACKUP_REPOS", json.dumps([
    {"name": "workflow", "path": str(BASE_DIR.parent),
     "remote": "origin"},
])))

backup_process: subprocess.Popen | None = None


def load_full_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


def save_config(config: dict):
    fd, tmp = tempfile.mkstemp(dir=BASE_DIR, suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(config, f, indent=2)
            f.write("\n")
        os.replace(tmp, CONFIG_PATH)
    except BaseException:
        os.unlink(tmp)
        raise


def modify_config(fn):
    with open(LOCK_PATH, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        config = load_full_config()
        result = fn(config)
        save_config(config)
        return result


@asynccontextmanager
async def lifespan(app_instance):
    for app_config in load_config():
        if app_config.get("autostart") and not all(
            is_port_listening(s["port"]) for s in app_config["services"]
        ):
            if app_config.get("type") == "compose":
                start_compose(app_config)
            else:
                app_procs = {}
                for svc in app_config["services"]:
                    if not is_port_listening(svc["port"]):
                        app_procs[svc["name"]] = start_service(app_config["id"], svc)
                processes[app_config["id"]] = app_procs
    yield


app = FastAPI(lifespan=lifespan)


def load_config() -> list[dict]:
    with open(CONFIG_PATH) as f:
        return json.load(f)["apps"]


def is_port_listening(port: int) -> bool:
    for family, addr in [(socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")]:
        with socket.socket(family, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            if s.connect_ex((addr, port)) == 0:
                return True
    return False


def get_app_status(app_config: dict) -> dict:
    services = []
    for svc in app_config["services"]:
        running = is_port_listening(svc["port"])
        services.append({
            "name": svc["name"],
            "port": svc["port"],
            "running": running,
        })

    all_running = all(s["running"] for s in services)
    any_running = any(s["running"] for s in services)

    if all_running:
        status = "running"
    elif any_running:
        status = "partial"
    else:
        status = "stopped"

    return {
        "id": app_config["id"],
        "name": app_config["name"],
        "description": app_config.get("description", ""),
        "url": app_config.get("url", ""),
        "autostart": app_config.get("autostart", False),
        "tags": app_config.get("tags", []),
        "status": status,
        "services": services,
    }


def _detect_compose_runtime() -> list[str]:
    for candidate in [["podman-compose"], ["docker", "compose"], ["docker-compose"]]:
        try:
            subprocess.run(
                candidate + ["version"],
                capture_output=True, timeout=5,
            )
            return candidate
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return ["podman-compose"]

_COMPOSE_RUNTIME = _detect_compose_runtime()


def compose_cmd(app_config: dict) -> list[str]:
    cfg = app_config["compose"]
    cmd = list(_COMPOSE_RUNTIME) + ["-f", cfg["file"]]
    if cfg.get("env_file"):
        cmd += ["--env-file", cfg["env_file"]]
    return cmd


def start_compose(app_config: dict):
    subprocess.Popen(
        compose_cmd(app_config) + ["up", "-d"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def stop_compose(app_config: dict):
    subprocess.run(
        compose_cmd(app_config) + ["down"],
        capture_output=True, timeout=60,
    )


def start_service(app_id: str, svc: dict) -> subprocess.Popen:
    LOGS_DIR.mkdir(exist_ok=True)
    log_file = LOGS_DIR / f"{app_id}_{svc['name']}.log"
    log = open(log_file, "a")
    proc = subprocess.Popen(
        shlex.split(svc["command"]),
        cwd=svc["directory"],
        stdout=log,
        stderr=log,
        start_new_session=True,
    )
    log.close()
    return proc


def kill_on_port(port: int):
    try:
        result = subprocess.run(
            ["lsof", "-t", f"-i:{port}"],
            capture_output=True, text=True, timeout=5,
        )
        if result.stdout.strip():
            for pid_str in result.stdout.strip().split("\n"):
                try:
                    pid = int(pid_str)
                except ValueError:
                    continue
                try:
                    os.killpg(os.getpgid(pid), signal.SIGTERM)
                except (ProcessLookupError, PermissionError):
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except (ProcessLookupError, PermissionError):
                        pass
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass


@app.get("/api/apps")
def list_apps():
    config = load_config()
    return [get_app_status(a) for a in config]


@app.post("/api/apps/{app_id}/start")
def start_app(app_id: str):
    config = load_config()
    app_config = next((a for a in config if a["id"] == app_id), None)
    if not app_config:
        raise HTTPException(404, "App not found")

    if all(is_port_listening(s["port"]) for s in app_config["services"]):
        raise HTTPException(409, "App is already running")

    if app_config.get("type") == "compose":
        start_compose(app_config)
        return {"status": "starting"}

    app_procs = processes.get(app_id, {})
    for svc in app_config["services"]:
        if not is_port_listening(svc["port"]):
            proc = start_service(app_id, svc)
            app_procs[svc["name"]] = proc
    processes[app_id] = app_procs
    return {"status": "starting"}


@app.post("/api/apps/{app_id}/stop")
def stop_app(app_id: str):
    config = load_config()
    app_config = next((a for a in config if a["id"] == app_id), None)
    if not app_config:
        raise HTTPException(404, "App not found")

    if app_config.get("type") == "compose":
        stop_compose(app_config)
        return {"status": "stopping"}

    if app_id in processes:
        for name, proc in processes[app_id].items():
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass
        del processes[app_id]

    for svc in app_config["services"]:
        if is_port_listening(svc["port"]):
            kill_on_port(svc["port"])

    return {"status": "stopping"}


@app.post("/api/apps/{app_id}/restart")
def restart_app(app_id: str):
    config = load_config()
    app_config = next((a for a in config if a["id"] == app_id), None)
    if not app_config:
        raise HTTPException(404, "App not found")

    stop_app(app_id)

    for _ in range(20):
        if not any(is_port_listening(s["port"]) for s in app_config["services"]):
            break
        time.sleep(0.5)

    return start_app(app_id)


@app.put("/api/apps/{app_id}/autostart")
def toggle_autostart(app_id: str):
    def _toggle(config):
        app_config = next((a for a in config["apps"] if a["id"] == app_id), None)
        if not app_config:
            raise HTTPException(404, "App not found")
        app_config["autostart"] = not app_config.get("autostart", False)
        return {"autostart": app_config["autostart"]}
    return modify_config(_toggle)


@app.put("/api/apps/order")
def reorder_apps(order: list[str] = Body()):
    def _reorder(config):
        apps_by_id = {a["id"]: a for a in config["apps"]}
        seen = set()
        reordered = []
        for app_id in order:
            if app_id in apps_by_id and app_id not in seen:
                reordered.append(apps_by_id[app_id])
                seen.add(app_id)
        for a in config["apps"]:
            if a["id"] not in seen:
                reordered.append(a)
        config["apps"] = reordered
        return {"status": "ok"}
    return modify_config(_reorder)


@app.get("/api/apps/{app_id}/logs")
def get_logs(app_id: str, service: str = "", lines: int = 50):
    lines = min(lines, 1000)
    config = load_config()
    app_config = next((a for a in config if a["id"] == app_id), None)
    if not app_config:
        raise HTTPException(404, "App not found")

    if app_config.get("type") == "compose":
        logs = {}
        for svc in app_config["services"]:
            if service and svc["name"] != service:
                continue
            result = subprocess.run(
                compose_cmd(app_config) + ["logs", "--tail", str(lines), svc["name"]],
                capture_output=True, text=True, timeout=10,
            )
            logs[svc["name"]] = result.stdout or result.stderr or ""
        return logs

    logs = {}
    for svc in app_config["services"]:
        if service and svc["name"] != service:
            continue
        log_file = LOGS_DIR / f"{app_id}_{svc['name']}.log"
        if log_file.exists():
            result = subprocess.run(
                ["tail", "-n", str(lines), str(log_file)],
                capture_output=True, text=True, timeout=5,
            )
            logs[svc["name"]] = result.stdout
        else:
            logs[svc["name"]] = ""
    return logs


@app.get("/")
def index():
    css_mtime = int((BASE_DIR / "static" / "style.css").stat().st_mtime)
    js_mtime = int((BASE_DIR / "static" / "app.js").stat().st_mtime)
    html = (BASE_DIR / "static" / "index.html").read_text()
    html = html.replace('"/static/style.css"', f'"/static/style.css?v={css_mtime}"')
    html = html.replace('"/static/app.js"', f'"/static/app.js?v={js_mtime}"')
    return HTMLResponse(html)


def parse_backup_log() -> dict:
    if not BACKUP_LOG.exists():
        return {"timestamp": None, "results": {}}

    try:
        text = BACKUP_LOG.read_text()
    except OSError:
        return {"timestamp": None, "results": {}}

    blocks = text.split("--- Backup started ---")
    if len(blocks) < 2:
        return {"timestamp": None, "results": {}}

    last_block = blocks[-1]
    results = {}
    timestamp = None

    for line in last_block.strip().splitlines():
        line = line.strip()
        if not line or "--- Backup complete ---" in line:
            continue

        ts_match = line.split("]")[0].lstrip("[") if line.startswith("[") else None
        if ts_match and not timestamp:
            timestamp = ts_match

        content = line.split("] ", 1)[-1] if "] " in line else line

        for repo in BACKUP_REPOS:
            name = repo["name"]
            if content.startswith(f"{name}: "):
                msg = content[len(name) + 2:]
                if "pushed" in msg and "failed" not in msg and "skipped" not in msg:
                    if results.get(name) != "no changes":
                        results[name] = "pushed"
                elif "push failed" in msg:
                    results[name] = "push failed"
                elif "skipped" in msg:
                    results[name] = "skipped"
                elif "no changes" in msg:
                    results[name] = "no changes"
                elif "committed" in msg:
                    results.setdefault(name, "committed")

    return {"timestamp": timestamp, "results": results}


def get_repo_git_info(repo: dict) -> dict:
    path = repo["path"]
    remote = repo["remote"]
    branch_result = subprocess.run(
        ["git", "-C", path, "symbolic-ref", "--short", "HEAD"],
        capture_output=True, text=True, timeout=5,
    )
    branch = branch_result.stdout.strip() or "main"

    hash_result = subprocess.run(
        ["git", "-C", path, "log", "-1", "--format=%H %ci"],
        capture_output=True, text=True, timeout=5,
    )
    parts = hash_result.stdout.strip().split(" ", 1)
    commit_hash = parts[0][:7] if parts else ""
    commit_time = parts[1] if len(parts) > 1 else ""

    ahead_result = subprocess.run(
        ["git", "-C", path, "rev-list", "--count", f"{remote}/{branch}..HEAD"],
        capture_output=True, text=True, timeout=5,
    )
    try:
        ahead = int(ahead_result.stdout.strip())
    except (ValueError, AttributeError):
        ahead = -1

    pushed_result = subprocess.run(
        ["git", "-C", path, "log", "-1", "--format=%H %ci", f"{remote}/{branch}"],
        capture_output=True, text=True, timeout=5,
    )
    pushed_parts = pushed_result.stdout.strip().split(" ", 1)
    pushed_hash = pushed_parts[0][:7] if pushed_parts else ""
    pushed_time = pushed_parts[1] if len(pushed_parts) > 1 else ""

    return {
        "commit_hash": commit_hash,
        "commit_time": commit_time,
        "pushed_hash": pushed_hash,
        "pushed_time": pushed_time,
        "commit_url": f"{repo.get('remote_url', '')}/commit/{pushed_hash}" if pushed_hash and repo.get('remote_url') else "",
        "ahead": ahead,
    }


@app.get("/api/backup/status")
def backup_status():
    global backup_process

    log_data = parse_backup_log()

    if backup_process and backup_process.poll() is not None:
        backup_process = None

    running = backup_process is not None
    if not running:
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", "workflow-backup.service"],
                capture_output=True, text=True, timeout=5,
            )
            running = result.stdout.strip() == "activating"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    next_run = None
    try:
        result = subprocess.run(
            ["systemctl", "--user", "show", "workflow-backup.timer",
             "--property=NextElapseUSecRealtime"],
            capture_output=True, text=True, timeout=5,
        )
        val = result.stdout.strip().split("=", 1)[-1]
        if val and val != "n/a":
            next_run = val
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    repos = []
    issues = []
    for repo in BACKUP_REPOS:
        try:
            git_info = get_repo_git_info(repo)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            git_info = {"commit_hash": "", "commit_time": "", "pushed_hash": "",
                        "commit_url": "", "ahead": -1}

        push_result = log_data["results"].get(repo["name"], "unknown")

        repos.append({
            "name": repo["name"],
            "last_push_result": push_result,
            **git_info,
        })

        if push_result in ("push failed", "skipped"):
            issues.append(f"{repo['name']}: {push_result}")

    if not log_data["timestamp"]:
        overall = "error"
    elif all(r["last_push_result"] in ("pushed", "no changes", "pushed to remote")
             for r in repos):
        overall = "ok"
    elif any(r["last_push_result"] in ("push failed", "skipped") for r in repos):
        overall = "warning"
    else:
        overall = "ok"

    return {
        "status": overall,
        "last_run": log_data["timestamp"],
        "next_run": next_run,
        "running": running,
        "repos": repos,
        "issues": issues,
    }


@app.post("/api/backup/run")
def run_backup():
    global backup_process
    if backup_process and backup_process.poll() is None:
        raise HTTPException(409, "Backup is already running")

    backup_process = subprocess.Popen(
        [str(BACKUP_SCRIPT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return {"status": "started"}


@app.post("/api/backup/stop")
def stop_backup():
    global backup_process
    if not backup_process or backup_process.poll() is not None:
        backup_process = None
        raise HTTPException(409, "No backup is running")

    try:
        os.killpg(os.getpgid(backup_process.pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        try:
            backup_process.kill()
        except (ProcessLookupError, PermissionError):
            pass

    backup_process = None
    return {"status": "stopped"}


@app.get("/api/backup/logs")
def backup_logs(lines: int = 80):
    lines = min(lines, 500)
    if not BACKUP_LOG.exists():
        return {"logs": "(no backup log found)"}
    try:
        result = subprocess.run(
            ["tail", "-n", str(lines), str(BACKUP_LOG)],
            capture_output=True, text=True, timeout=5,
        )
        return {"logs": result.stdout}
    except subprocess.TimeoutExpired:
        return {"logs": "(timeout reading log)"}


app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9000)
