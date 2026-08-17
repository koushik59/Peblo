import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class PublishRun(Base):
    __tablename__ = "publish_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    published_by: Mapped[str] = mapped_column(String(255), nullable=False)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # success, failed
    show_count: Mapped[int] = mapped_column(Integer, default=0)
    episode_count: Mapped[int] = mapped_column(Integer, default=0)
    catalogue_version: Mapped[str] = mapped_column(String(100), nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
