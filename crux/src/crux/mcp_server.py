from mcp.server.fastmcp import FastMCP
from datetime import datetime, timezone
from crux.db.models import get_session, Task, Label, Comment, Status, Priority

mcp = FastMCP("crux", instructions="""Personal task manager (Kanban board).

Statuses: todo → doing → review → done (with blocked as a side-state, archived for won't-do items).

Assignee convention: set assignee to track who owns a task. Use your name for the human, "Worker" for an AI agent.

Workflow: agents should add_task with assignee, move to doing when starting work, move to review when done. Only the human moves tasks to done. Use archived for items explicitly decided not to do (won't-do) — distinct from done (completed) and delete (removed).

Estimates: optional t-shirt sizes — XS (~15 min), S (~30 min), M (~1 hr), L (~2-3 hr), XL (~half day).

Today flag: use edit_task(today=True) to flag a task for daily focus. Use list_tasks(today=True) to see today's tasks. Flag auto-clears when task moves to done or archived.

Deep Work flag: use edit_task(deep_work=True) to flag a task for deep work focus. Use list_tasks(deep_work=True) to see deep work tasks. Flag auto-clears when task moves to done or archived.

Use add_comment to log progress, decisions, or blockers on a task.""")


def _parse_status(value: str) -> Status:
    try:
        return Status(value)
    except ValueError:
        raise ValueError(f"Invalid status '{value}'. Valid: {', '.join(s.value for s in Status)}")


def _parse_priority(value: str) -> Priority:
    try:
        return Priority(value)
    except ValueError:
        raise ValueError(f"Invalid priority '{value}'. Valid: {', '.join(p.value for p in Priority)}")


@mcp.tool()
def list_tasks(status: str | None = None, label: str | None = None,
               priority: str | None = None, assignee: str | None = None,
               today: bool | None = None, deep_work: bool | None = None) -> list[dict]:
    """List tasks, optionally filtered by status, label, priority, assignee, or today flag.

    Args:
        status: Filter by status (todo, doing, review, blocked, done, archived).
        label: Filter by label name.
        priority: Filter by priority (low, medium, high).
        assignee: Filter by assignee name.
        today: Filter to tasks flagged for today focus.
        deep_work: Filter to tasks flagged for deep work focus.
    """
    session = get_session()
    try:
        query = session.query(Task)
        if status:
            query = query.filter(Task.status == _parse_status(status))
        if priority:
            query = query.filter(Task.priority == _parse_priority(priority))
        if label:
            query = query.filter(Task.labels.any(Label.name == label.strip().lower()))
        if assignee:
            query = query.filter(Task.assignee == assignee)
        if today:
            query = query.filter(Task.today == 1)
        if deep_work:
            query = query.filter(Task.deep_work == 1)
        tasks = query.order_by(Task.position, Task.created_at).all()
        return [t.to_dict() for t in tasks]
    finally:
        session.close()


@mcp.tool()
def add_task(title: str, description: str | None = None, due_date: str | None = None,
             priority: str | None = None, labels: list[str] | None = None,
             status: str = "todo", assignee: str | None = None,
             estimate: str | None = None) -> dict:
    """Add a new task.

    Args:
        title: Task title (required).
        description: Optional description.
        due_date: Optional due date in YYYY-MM-DD format.
        priority: Optional priority (low, medium, high).
        labels: Optional list of label names.
        status: Initial status (default: todo).
        assignee: Optional assignee name.
        estimate: Optional size estimate (XS, S, M, L, XL).
    """
    session = get_session()
    try:
        from sqlalchemy import func
        parsed_status = _parse_status(status) if status else Status.TODO
        max_pos = session.query(func.max(Task.position)).filter(Task.status == parsed_status).scalar()
        task = Task(
            title=title,
            description=description,
            due_date=due_date,
            priority=_parse_priority(priority) if priority else None,
            status=parsed_status,
            position=(max_pos + 1) if max_pos is not None else 0,
            assignee=assignee,
            estimate=estimate.upper() if estimate else None,
            done_at=datetime.now(timezone.utc) if parsed_status in (Status.DONE, Status.ARCHIVED) else None,
        )
        if labels:
            task_labels = []
            for name in labels:
                name = name.strip().lower()
                label = session.query(Label).filter(Label.name == name).first()
                if not label:
                    label = Label(name=name)
                    session.add(label)
                task_labels.append(label)
            task.labels = task_labels
        session.add(task)
        session.commit()
        return task.to_dict()
    finally:
        session.close()


@mcp.tool()
def edit_task(task_id: int, title: str | None = None, description: str | None = None,
              due_date: str | None = None, priority: str | None = None,
              labels: list[str] | None = None, assignee: str | None = None,
              estimate: str | None = None, today: bool | None = None,
              deep_work: bool | None = None) -> dict:
    """Edit an existing task's fields. Pass empty string for assignee to unassign.

    Args:
        task_id: ID of the task to edit.
        title: New title.
        description: New description.
        due_date: New due date (YYYY-MM-DD).
        priority: New priority (low, medium, high).
        labels: New labels (replaces existing).
        assignee: New assignee (empty string to unassign).
        estimate: New size estimate (XS, S, M, L, XL).
        today: Flag task for today focus (true/false).
        deep_work: Flag task for deep work focus (true/false).
    """
    session = get_session()
    try:
        task = session.get(Task, task_id)
        if not task:
            return {"error": f"Task #{task_id} not found"}
        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if due_date is not None:
            task.due_date = due_date
        if priority is not None:
            task.priority = _parse_priority(priority)
        if assignee is not None:
            task.assignee = assignee if assignee else None
        if estimate is not None:
            task.estimate = estimate.upper() if estimate else None
        has_label_change = labels is not None
        if has_label_change:
            task_labels = []
            for name in labels:
                name = name.strip().lower()
                if not name:
                    continue
                label = session.query(Label).filter(Label.name == name).first()
                if not label:
                    label = Label(name=name)
                    session.add(label)
                task_labels.append(label)
            task.labels = task_labels
        if today is not None:
            if today and task.status not in (Status.DONE, Status.ARCHIVED):
                task.today = 1
                from sqlalchemy import func
                max_tp = session.query(func.max(Task.today_position)).filter(Task.today == 1, Task.id != task_id).scalar()
                task.today_position = (max_tp + 1) if max_tp is not None else 0
            elif not today:
                task.today = 0
        if deep_work is not None:
            if deep_work and task.status not in (Status.DONE, Status.ARCHIVED):
                task.deep_work = 1
                from sqlalchemy import func
                max_dp = session.query(func.max(Task.deep_work_position)).filter(Task.deep_work == 1, Task.id != task_id).scalar()
                task.deep_work_position = (max_dp + 1) if max_dp is not None else 0
            elif not deep_work:
                task.deep_work = 0
        session.commit()
        if has_label_change:
            for label in session.query(Label).all():
                if not label.tasks:
                    session.delete(label)
            session.commit()
        return task.to_dict()
    finally:
        session.close()


@mcp.tool()
def move_task(task_id: int, status: str) -> dict:
    """Move a task to a different status column.

    Args:
        task_id: ID of the task to move.
        status: New status (todo, doing, review, blocked, done, archived).
    """
    session = get_session()
    try:
        task = session.get(Task, task_id)
        if not task:
            return {"error": f"Task #{task_id} not found"}
        new_status = _parse_status(status)
        terminal = {Status.DONE, Status.ARCHIVED}
        entering_terminal = new_status in terminal and task.status not in terminal
        leaving_terminal = new_status not in terminal and task.status in terminal
        if entering_terminal:
            task.done_at = datetime.now(timezone.utc)
            task.today = 0
            task.deep_work = 0
        elif leaving_terminal:
            task.done_at = None
        task.status = new_status
        if entering_terminal:
            siblings = (session.query(Task)
                        .filter(Task.status == new_status, Task.id != task.id)
                        .order_by(Task.position, Task.created_at)
                        .all())
            task.position = 0
            for i, t in enumerate(siblings):
                t.position = i + 1
        session.commit()
        return task.to_dict()
    finally:
        session.close()


@mcp.tool()
def delete_task(task_id: int) -> dict:
    """Permanently delete a task.

    Args:
        task_id: ID of the task to delete.
    """
    session = get_session()
    try:
        task = session.get(Task, task_id)
        if not task:
            return {"error": f"Task #{task_id} not found"}
        session.delete(task)
        session.commit()
        for label in session.query(Label).all():
            if not label.tasks:
                session.delete(label)
        session.commit()
        return {"deleted": task_id}
    finally:
        session.close()


@mcp.tool()
def list_labels() -> list[str]:
    """List all defined labels."""
    session = get_session()
    try:
        labels = session.query(Label).order_by(Label.name).all()
        return [l.name for l in labels]
    finally:
        session.close()


@mcp.tool()
def get_task(task_id: int) -> dict:
    """Get a single task with full details including comments.

    Args:
        task_id: ID of the task to fetch.
    """
    session = get_session()
    try:
        task = session.get(Task, task_id)
        if not task:
            return {"error": f"Task #{task_id} not found"}
        return task.to_dict()
    finally:
        session.close()


@mcp.tool()
def search_tasks(query: str, status: str | None = None,
                 label: str | None = None, priority: str | None = None) -> list[dict]:
    """Search tasks by text in title, description, checklist items, or comments.

    Args:
        query: Search text (case-insensitive substring match).
        status: Optional status filter.
        label: Optional label filter.
        priority: Optional priority filter.
    """
    session = get_session()
    try:
        q = session.query(Task).outerjoin(Comment).filter(
            (Task.title.ilike(f"%{query}%"))
            | (Task.description.ilike(f"%{query}%"))
            | (Task.checklist.ilike(f"%{query}%"))
            | (Comment.text.ilike(f"%{query}%"))
        ).distinct()
        if status:
            q = q.filter(Task.status == _parse_status(status))
        if priority:
            q = q.filter(Task.priority == _parse_priority(priority))
        if label:
            q = q.filter(Task.labels.any(Label.name == label.strip().lower()))
        tasks = q.order_by(Task.created_at.desc()).all()
        return [t.to_dict() for t in tasks]
    finally:
        session.close()


@mcp.tool()
def assign_task(task_id: int, assignee: str | None = None) -> dict:
    """Assign or unassign a task. Omit assignee to unassign.

    Args:
        task_id: ID of the task.
        assignee: Name to assign (e.g. "Me", "Worker"). Omit to unassign.
    """
    session = get_session()
    try:
        task = session.get(Task, task_id)
        if not task:
            return {"error": f"Task #{task_id} not found"}
        task.assignee = assignee
        session.commit()
        return task.to_dict()
    finally:
        session.close()


@mcp.tool()
def add_comment(task_id: int, text: str, author: str = "Worker") -> dict:
    """Add a comment to a task. Use for progress updates, decisions, or blockers.

    Args:
        task_id: ID of the task.
        text: Comment text.
        author: Who is commenting (default: "Worker").
    """
    session = get_session()
    try:
        task = session.get(Task, task_id)
        if not task:
            return {"error": f"Task #{task_id} not found"}
        comment = Comment(task_id=task_id, text=text, author=author)
        session.add(comment)
        session.commit()
        return comment.to_dict()
    finally:
        session.close()


@mcp.tool()
def edit_comment(comment_id: int, text: str) -> dict:
    """Edit an existing comment's text.

    Args:
        comment_id: ID of the comment to edit.
        text: New comment text.
    """
    session = get_session()
    try:
        comment = session.get(Comment, comment_id)
        if not comment:
            return {"error": f"Comment #{comment_id} not found"}
        comment.text = text
        session.commit()
        return comment.to_dict()
    finally:
        session.close()


@mcp.tool()
def delete_comment(comment_id: int) -> dict:
    """Delete a comment.

    Args:
        comment_id: ID of the comment to delete.
    """
    session = get_session()
    try:
        comment = session.get(Comment, comment_id)
        if not comment:
            return {"error": f"Comment #{comment_id} not found"}
        session.delete(comment)
        session.commit()
        return {"deleted": comment_id}
    finally:
        session.close()


def main():
    mcp.run()


if __name__ == "__main__":
    main()
