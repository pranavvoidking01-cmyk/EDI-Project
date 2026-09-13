from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, create_engine, inspect, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from backend.nlp_engine import ALERT_PREFIX, analyze_message
from backend.recommender import recommend_priority_keywords
from backend.scoring_engine import calculate_priority_score

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = f"sqlite:///{BASE_DIR / 'chat.db'}"
PRIORITY_THRESHOLD = 0.7

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    messages: Mapped[list["Message"]] = relationship(back_populates="sender")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column("chat_id", Integer, default=1, nullable=False)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="sent", nullable=False)
    priority_score: Mapped[float] = mapped_column(default=0.0, nullable=False)
    sender: Mapped[User] = relationship(back_populates="messages")


class PriorityLog(Base):
    __tablename__ = "priority_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    previous_content: Mapped[str] = mapped_column(Text, nullable=False)
    original_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    description: Mapped[str] = mapped_column(String(240), nullable=False)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="todo", nullable=False)


class MessageCreate(BaseModel):
    group_id: int = Field(default=1, ge=1)
    sender_id: int
    content: str = Field(min_length=1, max_length=2000)
    priority_score: float = Field(default=0.0, ge=0.0, le=1.0)
    contact_priority_weight: float = Field(default=1.0, ge=0.0, le=1.0)
    group_muted: bool = False


class MessageUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    priority_score: float | None = Field(default=None, ge=0.0, le=1.0)
    status: str | None = Field(default=None, max_length=30)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    sender_id: int
    content: str
    timestamp: datetime
    status: str
    priority_score: float


class TaskCreate(BaseModel):
    description: str = Field(min_length=1, max_length=240)
    deadline: datetime | None = None
    status: str = Field(default="todo", max_length=30)


class TaskResponse(TaskCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


Base.metadata.create_all(bind=engine)


def ensure_priority_log_schema() -> None:
    columns = {column["name"] for column in inspect(engine).get_columns("priority_logs")}
    if "original_timestamp" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE priority_logs ADD COLUMN original_timestamp DATETIME"))


def ensure_message_schema() -> None:
    columns = {column["name"] for column in inspect(engine).get_columns("messages")}
    if "chat_id" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE messages ADD COLUMN chat_id INTEGER NOT NULL DEFAULT 1"))


ensure_priority_log_schema()
ensure_message_schema()
app = FastAPI(title="Pulse Chat API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_default_user(db: Session) -> None:
    contacts = (
        (1, "Local User", "local@example.com"),
        (2, "Maya Khan", "maya@example.com"),
        (3, "Jordan Tan", "jordan@example.com"),
    )
    for user_id, name, email in contacts:
        if db.get(User, user_id) is None:
            db.add(User(id=user_id, name=name, email=email))
    if db.new:
        db.commit()


@app.on_event("startup")
def seed_database() -> None:
    with SessionLocal() as db:
        ensure_default_user(db)


@app.get("/api/messages", response_model=list[MessageResponse])
def list_messages(
    group_id: int | None = Query(default=None, ge=1),
    chat_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    selected_group = group_id if group_id is not None else chat_id
    query = select(Message).order_by(Message.timestamp.asc())
    if selected_group is not None:
        query = query.where(Message.group_id == selected_group)
    return db.scalars(
        query
    ).all()


@app.get("/api/priority-logs")
def list_priority_logs(db: Session = Depends(get_db)):
    logs = db.scalars(
        select(PriorityLog).order_by(
            PriorityLog.original_timestamp.desc(), PriorityLog.logged_at.desc()
        )
    ).all()
    return [
        {
            "id": log.id,
            "message_id": log.message_id,
            "action": log.action,
            "previous_content": log.previous_content,
            "original_timestamp": log.original_timestamp,
            "logged_at": log.logged_at,
        }
        for log in logs
    ]


@app.get("/api/recommendations", response_model=list[str])
def list_recommendations(db: Session = Depends(get_db)):
    return recommend_priority_keywords(db)


@app.get("/api/tasks", response_model=list[TaskResponse])
def list_tasks(db: Session = Depends(get_db)):
    return db.scalars(select(Task).order_by(Task.deadline.asc(), Task.id.asc())).all()


@app.post("/api/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    task = Task(**payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@app.put("/api/tasks/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, payload: TaskCreate, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    for key, value in payload.model_dump().items():
        setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return task


@app.delete("/api/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()


@app.post("/api/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def create_message(payload: MessageCreate, db: Session = Depends(get_db)):
    if db.get(User, payload.sender_id) is None:
        raise HTTPException(status_code=404, detail="Sender not found")
    analysis = analyze_message(payload.content)
    message = Message(
        group_id=payload.group_id,
        sender_id=payload.sender_id,
        content=analysis.content,
        priority_score=max(
            payload.priority_score,
            calculate_priority_score(
                tier=analysis.tier,
                temporal_entities=analysis.temporal_entities,
                contact_priority_weight=payload.contact_priority_weight,
                group_muted=payload.group_muted,
            ),
        ),
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@app.put("/api/messages/{message_id}", response_model=MessageResponse)
def update_message(message_id: int, payload: MessageUpdate, db: Session = Depends(get_db)):
    message = db.get(Message, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    if message.content.startswith(ALERT_PREFIX):
        db.add(
            PriorityLog(
                message_id=message.id,
                action="modified",
                previous_content=message.content,
                original_timestamp=message.timestamp,
            )
        )
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(message, key, value)
    message.status = "edited"
    db.commit()
    db.refresh(message)
    return message


@app.delete("/api/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(message_id: int, db: Session = Depends(get_db)):
    message = db.get(Message, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    if message.content.startswith(ALERT_PREFIX):
        db.add(
            PriorityLog(
                message_id=message.id,
                action="deleted",
                previous_content=message.content,
                original_timestamp=message.timestamp,
            )
        )
    db.delete(message)
    db.commit()


app.mount("/", StaticFiles(directory=BASE_DIR / "frontend", html=True), name="frontend")
