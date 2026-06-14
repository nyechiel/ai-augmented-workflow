import enum
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Enum as SAEnum, Table, ForeignKey, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, backref

DB_DIR = Path.home() / ".crux"
DB_PATH = DB_DIR / "crux.db"

Base = declarative_base()


class Status(str, enum.Enum):
    TODO = "todo"
    DOING = "doing"
    REVIEW = "review"
    BLOCKED = "blocked"
    DONE = "done"
    ARCHIVED = "archived"


class Priority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


task_labels = Table(
    "task_labels",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("label_id", Integer, ForeignKey("labels.id", ondelete="CASCADE"), primary_key=True),
)


class Label(Base):
    __tablename__ = "labels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)

    def to_dict(self):
        return {"id": self.id, "name": self.name}


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    due_date = Column(String, nullable=True)
    priority = Column(SAEnum(Priority), nullable=True)
    status = Column(SAEnum(Status), nullable=False, default=Status.TODO)
    position = Column(Integer, nullable=False, default=0)
    estimate = Column(String, nullable=True)
    checklist = Column(String, nullable=True)  # JSON: [{"text":"...", "done": false}, ...]
    assignee = Column(String, nullable=True)
    today = Column(Integer, nullable=False, default=0)
    today_position = Column(Integer, nullable=False, default=0)
    deep_work = Column(Integer, nullable=False, default=0)
    deep_work_position = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    done_at = Column(DateTime, nullable=True)
    labels = relationship("Label", secondary=task_labels, backref="tasks")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "due_date": self.due_date,
            "priority": self.priority.value if self.priority else None,
            "status": self.status.value,
            "position": self.position,
            "estimate": self.estimate,
            "checklist": json.loads(self.checklist) if self.checklist else [],
            "assignee": self.assignee,
            "today": bool(self.today),
            "today_position": self.today_position,
            "deep_work": bool(self.deep_work),
            "deep_work_position": self.deep_work_position,
            "labels": [l.name for l in self.labels],
            "comments": [c.to_dict() for c in self.comments] if self.comments else [],
            "created_at": (self.created_at.isoformat() + "Z") if self.created_at else None,
            "updated_at": (self.updated_at.isoformat() + "Z") if self.updated_at else None,
            "done_at": (self.done_at.isoformat() + "Z") if self.done_at else None,
        }


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    text = Column(String, nullable=False)
    author = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    task = relationship("Task", backref=backref("comments", cascade="all, delete-orphan"))

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "text": self.text,
            "author": self.author,
            "created_at": (self.created_at.isoformat() + "Z") if self.created_at else None,
        }


def _migrate(engine):
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    if "tasks" in inspector.get_table_names():
        columns = [c["name"] for c in inspector.get_columns("tasks")]
        if "position" not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE tasks ADD COLUMN position INTEGER NOT NULL DEFAULT 0"))
                conn.commit()
        if "estimate" not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE tasks ADD COLUMN estimate TEXT"))
                conn.commit()
        if "checklist" not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE tasks ADD COLUMN checklist TEXT"))
                conn.commit()
        if "assignee" not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE tasks ADD COLUMN assignee TEXT"))
                conn.commit()
        if "done_at" not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE tasks ADD COLUMN done_at DATETIME"))
                conn.commit()
        if "today" not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE tasks ADD COLUMN today INTEGER NOT NULL DEFAULT 0"))
                conn.commit()
        if "today_position" not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE tasks ADD COLUMN today_position INTEGER NOT NULL DEFAULT 0"))
                conn.commit()
        if "deep_work" not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE tasks ADD COLUMN deep_work INTEGER NOT NULL DEFAULT 0"))
                conn.commit()
        if "deep_work_position" not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE tasks ADD COLUMN deep_work_position INTEGER NOT NULL DEFAULT 0"))
                conn.commit()


_engine = None
_Session = None


def get_engine():
    global _engine
    if _engine is None:
        DB_DIR.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            f"sqlite:///{DB_PATH}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        with _engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.commit()
        _migrate(_engine)
        Base.metadata.create_all(_engine)
    return _engine


def get_session():
    global _Session
    if _Session is None:
        _Session = sessionmaker(bind=get_engine())
    return _Session()
