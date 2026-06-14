from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
from sqlalchemy import func
from crux.db.models import get_session, Task, Label, Comment, Status, Priority
from datetime import datetime, timezone
import re

app = FastAPI()

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    due_date: str | None = None
    priority: str | None = None
    labels: list[str] | None = None
    estimate: str | None = None
    status: str | None = None
    checklist: list[dict] | None = None
    assignee: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    due_date: str | None = None
    priority: str | None = None
    status: str | None = None
    position: int | None = None
    labels: list[str] | None = None
    estimate: str | None = None
    checklist: list[dict] | None = None
    assignee: str | None = None
    today: bool | None = None
    deep_work: bool | None = None


class TodayReorderRequest(BaseModel):
    task_id: int
    position: int


class DeepWorkReorderRequest(BaseModel):
    task_id: int
    position: int


class CommentCreate(BaseModel):
    text: str
    author: str = "Worker"


class CommentUpdate(BaseModel):
    text: str


class ReorderRequest(BaseModel):
    task_id: int
    status: str
    position: int


ESTIMATE_SIZES = ["XS", "S", "M", "L", "XL"]


def _suggest_estimate(title, description, labels):
    text = f"{title or ''} {description or ''}".lower()
    label_names = [l.lower() for l in (labels or [])]
    url_count = len(re.findall(r"https?://", text))
    bullet_count = text.count("\n- ")
    has_research = "research" in label_names or "research" in text
    has_reading = "reading" in label_names or "reading" in text
    desc_len = len(description or "")

    if has_research or url_count >= 3 or desc_len > 500:
        return "L"
    if url_count >= 2 or bullet_count >= 3 or has_reading:
        return "M"
    if url_count == 1 or desc_len > 100:
        return "S"
    if desc_len > 0 or label_names:
        return "S"
    return "XS"


def _prune_orphan_labels(session):
    for label in session.query(Label).all():
        if not label.tasks:
            session.delete(label)
    session.commit()


def _sync_labels(session, task, label_names):
    labels = []
    for name in label_names:
        name = name.strip().lower()
        if not name:
            continue
        label = session.query(Label).filter(Label.name == name).first()
        if not label:
            label = Label(name=name)
            session.add(label)
        labels.append(label)
    task.labels = labels



@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/tasks")
def list_tasks():
    session = get_session()
    try:
        return [t.to_dict() for t in session.query(Task).order_by(Task.position, Task.created_at).all()]
    finally:
        session.close()


@app.get("/api/labels")
def list_labels():
    session = get_session()
    try:
        return [l.name for l in session.query(Label).order_by(Label.name).all()]
    finally:
        session.close()


@app.delete("/api/labels/prune")
def prune_labels():
    session = get_session()
    try:
        all_labels = session.query(Label).all()
        removed = 0
        for label in all_labels:
            if not label.tasks:
                session.delete(label)
                removed += 1
        session.commit()
        return {"removed": removed}
    finally:
        session.close()


def _parse_status(value: str) -> Status:
    try:
        return Status(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {value}")


def _parse_priority(value: str) -> Priority:
    try:
        return Priority(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid priority: {value}")


@app.post("/api/tasks")
def create_task(data: TaskCreate):
    session = get_session()
    try:
        status = _parse_status(data.status) if data.status else Status.TODO
        max_pos_val = session.query(func.max(Task.position)).filter(Task.status == status).scalar()
        max_pos = (max_pos_val + 1) if max_pos_val is not None else 0
        task = Task(
            title=data.title,
            description=data.description,
            due_date=data.due_date,
            priority=_parse_priority(data.priority) if data.priority else None,
            status=status,
            position=max_pos,
            assignee=data.assignee,
            done_at=datetime.now(timezone.utc) if status in (Status.DONE, Status.ARCHIVED) else None,
        )
        if data.labels:
            _sync_labels(session, task, data.labels)
        estimate = data.estimate if data.estimate in ESTIMATE_SIZES else None
        task.estimate = estimate or _suggest_estimate(data.title, data.description, data.labels)
        if data.checklist:
            import json
            task.checklist = json.dumps(data.checklist)
        session.add(task)
        session.commit()
        return task.to_dict()
    finally:
        session.close()


@app.patch("/api/tasks/{task_id}")
def update_task(task_id: int, data: TaskUpdate):
    session = get_session()
    try:
        task = session.get(Task, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if data.title is not None:
            task.title = data.title
        if data.description is not None:
            task.description = data.description or None
        if data.due_date is not None:
            task.due_date = data.due_date or None
        if data.priority is not None:
            task.priority = _parse_priority(data.priority) if data.priority else None
        if data.status is not None:
            new_status = _parse_status(data.status)
            terminal = {Status.DONE, Status.ARCHIVED}
            entering_terminal = new_status in terminal and task.status not in terminal
            leaving_terminal = new_status not in terminal and task.status in terminal
            task.status = new_status
            if entering_terminal:
                task.done_at = datetime.now(timezone.utc)
                task.today = 0
                task.deep_work = 0
            elif leaving_terminal:
                task.done_at = None
            if entering_terminal:
                siblings = (session.query(Task)
                            .filter(Task.status == new_status, Task.id != task.id)
                            .order_by(Task.position, Task.created_at)
                            .all())
                task.position = 0
                for i, t in enumerate(siblings):
                    t.position = i + 1
        if data.assignee is not None:
            task.assignee = data.assignee if data.assignee else None
        has_label_change = data.labels is not None
        if has_label_change:
            _sync_labels(session, task, data.labels)
        if data.estimate is not None:
            if data.estimate in ESTIMATE_SIZES:
                task.estimate = data.estimate
            else:
                labels = [l.name for l in task.labels]
                task.estimate = _suggest_estimate(task.title, task.description, labels)
        if data.checklist is not None:
            import json
            task.checklist = json.dumps(data.checklist) if data.checklist else None
        if data.today is not None:
            if data.today and task.status not in (Status.DONE, Status.ARCHIVED):
                task.today = 1
                max_tp = session.query(func.max(Task.today_position)).filter(Task.today == 1, Task.id != task.id).scalar()
                task.today_position = (max_tp + 1) if max_tp is not None else 0
            elif not data.today:
                task.today = 0
        if data.deep_work is not None:
            if data.deep_work and task.status not in (Status.DONE, Status.ARCHIVED):
                task.deep_work = 1
                max_dp = session.query(func.max(Task.deep_work_position)).filter(Task.deep_work == 1, Task.id != task.id).scalar()
                task.deep_work_position = (max_dp + 1) if max_dp is not None else 0
            elif not data.deep_work:
                task.deep_work = 0
        session.commit()
        if has_label_change:
            _prune_orphan_labels(session)
        return task.to_dict()
    finally:
        session.close()


@app.post("/api/tasks/reorder")
def reorder_task(data: ReorderRequest):
    session = get_session()
    try:
        task = session.get(Task, data.task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        new_status = _parse_status(data.status)
        siblings = (session.query(Task)
                    .filter(Task.status == new_status, Task.id != data.task_id)
                    .order_by(Task.position, Task.created_at)
                    .all())
        terminal = {Status.DONE, Status.ARCHIVED}
        pos = 0 if new_status in terminal else max(0, min(data.position, len(siblings)))
        siblings.insert(pos, task)
        if new_status in terminal and task.status not in terminal:
            task.done_at = datetime.now(timezone.utc)
            task.today = 0
            task.deep_work = 0
        elif new_status not in terminal and task.status in terminal:
            task.done_at = None
        task.status = new_status
        for i, t in enumerate(siblings):
            t.position = i
        session.commit()
        return {"ok": True}
    finally:
        session.close()


@app.post("/api/tasks/today-reorder")
def reorder_today(data: TodayReorderRequest):
    session = get_session()
    try:
        task = session.get(Task, data.task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if task.status in (Status.DONE, Status.ARCHIVED):
            raise HTTPException(status_code=400, detail="Cannot flag done or archived tasks for today")
        siblings = (session.query(Task)
                    .filter(Task.today == 1, Task.id != data.task_id)
                    .order_by(Task.today_position)
                    .all())
        task.today = 1
        pos = max(0, min(data.position, len(siblings)))
        siblings.insert(pos, task)
        for i, t in enumerate(siblings):
            t.today_position = i
        session.commit()
        return {"ok": True}
    finally:
        session.close()


@app.post("/api/tasks/deep-work-reorder")
def reorder_deep_work(data: DeepWorkReorderRequest):
    session = get_session()
    try:
        task = session.get(Task, data.task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if task.status in (Status.DONE, Status.ARCHIVED):
            raise HTTPException(status_code=400, detail="Cannot flag done or archived tasks for deep work")
        siblings = (session.query(Task)
                    .filter(Task.deep_work == 1, Task.id != data.task_id)
                    .order_by(Task.deep_work_position)
                    .all())
        task.deep_work = 1
        pos = max(0, min(data.position, len(siblings)))
        siblings.insert(pos, task)
        for i, t in enumerate(siblings):
            t.deep_work_position = i
        session.commit()
        return {"ok": True}
    finally:
        session.close()


@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int):
    session = get_session()
    try:
        task = session.get(Task, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        session.delete(task)
        session.commit()
        _prune_orphan_labels(session)
        return {"ok": True}
    finally:
        session.close()


@app.get("/api/tasks/{task_id}/comments")
def list_comments(task_id: int):
    session = get_session()
    try:
        task = session.get(Task, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return [c.to_dict() for c in task.comments]
    finally:
        session.close()


@app.post("/api/tasks/{task_id}/comments")
def create_comment(task_id: int, data: CommentCreate):
    session = get_session()
    try:
        task = session.get(Task, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        comment = Comment(task_id=task_id, text=data.text, author=data.author)
        session.add(comment)
        session.commit()
        return comment.to_dict()
    finally:
        session.close()


@app.patch("/api/comments/{comment_id}")
def update_comment(comment_id: int, data: CommentUpdate):
    session = get_session()
    try:
        comment = session.get(Comment, comment_id)
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")
        comment.text = data.text
        session.commit()
        return comment.to_dict()
    finally:
        session.close()


@app.delete("/api/comments/{comment_id}")
def delete_comment(comment_id: int):
    session = get_session()
    try:
        comment = session.get(Comment, comment_id)
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")
        session.delete(comment)
        session.commit()
        return {"ok": True}
    finally:
        session.close()
