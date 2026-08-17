from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, ForeignKey, DateTime, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

if TYPE_CHECKING:
    from app.models.season import Season
    from app.models.artwork import Artwork


class Episode(Base):
    __tablename__ = "episodes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    season_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)  # in seconds
    content_group: Mapped[str] = mapped_column(String(200), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False)  # en, hi, ta, etc.
    episode_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    season: Mapped[Season] = relationship("Season", back_populates="episodes")
    artworks: Mapped[list[Artwork]] = relationship(
        "Artwork", back_populates="episode", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("season_id", "episode_number", name="uq_season_episode_number"),
        UniqueConstraint("content_group", "language", name="uq_content_group_language"),
        Index("ix_episodes_season_id", "season_id"),
        Index("ix_episodes_content_group", "content_group"),
        Index("ix_episodes_language", "language"),
    )
