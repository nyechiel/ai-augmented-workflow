import click
from datetime import datetime, timezone
from crux.db.models import get_session, Task, Label, Status, Priority


@click.group()
def cli():
    """Personal task manager."""
    pass


def _get_or_create_labels(session, label_names):
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
    return labels


@cli.command()
@click.argument("title")
@click.option("--desc", default=None, help="Task description")
@click.option("--due", default=None, help="Due date (YYYY-MM-DD)")
@click.option("--priority", "-p", type=click.Choice(["low", "medium", "high"]), default=None)
@click.option("--label", "-l", multiple=True, help="Labels (repeatable)")
@click.option("--assignee", "-a", default=None, help="Assignee name")
def add(title, desc, due, priority, label, assignee):
    """Add a new task."""
    session = get_session()
    task = Task(
        title=title,
        description=desc,
        due_date=due,
        priority=Priority(priority) if priority else None,
        assignee=assignee,
    )
    if label:
        task.labels = _get_or_create_labels(session, label)
    session.add(task)
    session.commit()
    click.echo(f"Added task #{task.id}: {task.title}")
    session.close()


@cli.command(name="list")
@click.option("--status", "-s", type=click.Choice(["todo", "doing", "review", "blocked", "done", "archived"]), default=None)
@click.option("--priority", "-p", type=click.Choice(["low", "medium", "high"]), default=None)
@click.option("--label", "-l", default=None, help="Filter by label")
@click.option("--assignee", "-a", default=None, help="Filter by assignee")
def list_tasks(status, priority, label, assignee):
    """List tasks."""
    session = get_session()
    query = session.query(Task)
    if status:
        query = query.filter(Task.status == Status(status))
    if priority:
        query = query.filter(Task.priority == Priority(priority))
    if label:
        query = query.filter(Task.labels.any(Label.name == label.strip().lower()))
    if assignee:
        query = query.filter(Task.assignee == assignee)
    tasks = query.order_by(Task.position, Task.created_at).all()

    if not tasks:
        click.echo("No tasks found.")
        session.close()
        return

    for t in tasks:
        pri = f" [{t.priority.value}]" if t.priority else ""
        due = f" (due: {t.due_date})" if t.due_date else ""
        lbls = f" {' '.join('#' + l.name for l in t.labels)}" if t.labels else ""
        assignee_str = f" @{t.assignee}" if t.assignee else ""
        click.echo(f"  #{t.id}  [{t.status.value:>7}]{pri}  {t.title}{due}{lbls}{assignee_str}")
    session.close()


@cli.command()
@click.argument("task_id", type=int)
def start(task_id):
    """Move a task to 'doing'."""
    _move_task(task_id, Status.DOING)


@cli.command()
@click.argument("task_id", type=int)
def done(task_id):
    """Move a task to 'done'."""
    _move_task(task_id, Status.DONE)


@cli.command()
@click.argument("task_id", type=int)
def review(task_id):
    """Move a task to 'review'."""
    _move_task(task_id, Status.REVIEW)


@cli.command()
@click.argument("task_id", type=int)
def block(task_id):
    """Move a task to 'blocked'."""
    _move_task(task_id, Status.BLOCKED)


@cli.command()
@click.argument("task_id", type=int)
def archive(task_id):
    """Move a task to 'archived' (won't do)."""
    _move_task(task_id, Status.ARCHIVED)


def _move_task(task_id, new_status):
    session = get_session()
    task = session.get(Task, task_id)
    if not task:
        click.echo(f"Task #{task_id} not found.")
        session.close()
        return
    terminal = {Status.DONE, Status.ARCHIVED}
    if new_status in terminal and task.status not in terminal:
        task.done_at = datetime.now(timezone.utc)
        task.today = 0
        task.deep_work = 0
    elif new_status not in terminal and task.status in terminal:
        task.done_at = None
    task.status = new_status
    session.commit()
    click.echo(f"Task #{task_id} moved to '{new_status.value}'.")
    session.close()


@cli.command()
@click.argument("task_id", type=int)
@click.option("--title", default=None)
@click.option("--desc", default=None)
@click.option("--due", default=None)
@click.option("--priority", "-p", type=click.Choice(["low", "medium", "high"]), default=None)
@click.option("--label", "-l", multiple=True, help="Set labels (replaces existing)")
@click.option("--assignee", "-a", default=None, help="Set assignee (use '' to unassign)")
def edit(task_id, title, desc, due, priority, label, assignee):
    """Edit a task."""
    session = get_session()
    task = session.get(Task, task_id)
    if not task:
        click.echo(f"Task #{task_id} not found.")
        session.close()
        return
    if title is not None:
        task.title = title
    if desc is not None:
        task.description = desc
    if due is not None:
        task.due_date = due
    if priority is not None:
        task.priority = Priority(priority)
    if assignee is not None:
        task.assignee = assignee if assignee else None
    if label:
        task.labels = _get_or_create_labels(session, label)
    session.commit()
    click.echo(f"Task #{task_id} updated.")
    session.close()


@cli.command()
@click.argument("task_id", type=int)
@click.confirmation_option(prompt="Are you sure you want to delete this task?")
def rm(task_id):
    """Delete a task permanently."""
    session = get_session()
    task = session.get(Task, task_id)
    if not task:
        click.echo(f"Task #{task_id} not found.")
        session.close()
        return
    session.delete(task)
    session.commit()
    click.echo(f"Task #{task_id} deleted.")
    session.close()


@cli.command()
@click.option("--prune", is_flag=True, help="Remove labels not attached to any task")
def labels(prune):
    """List all labels, or prune unused ones."""
    session = get_session()
    all_labels = session.query(Label).order_by(Label.name).all()
    if not all_labels:
        click.echo("No labels defined.")
        session.close()
        return
    if prune:
        removed = 0
        for label in all_labels:
            if not label.tasks:
                session.delete(label)
                removed += 1
        session.commit()
        click.echo(f"Removed {removed} unused label(s).")
    else:
        for label in all_labels:
            count = len(label.tasks)
            click.echo(f"  {label.name} ({count} task{'s' if count != 1 else ''})")
    session.close()


@cli.command()
@click.option("--port", default=8487, help="Port for the web UI")
def web(port):
    """Launch the web UI."""
    import uvicorn
    from crux.web.server import app
    click.echo(f"Starting web UI at http://localhost:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
