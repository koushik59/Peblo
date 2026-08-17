import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, ForeignKey, DateTime, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class Episode(Base):
    __tablename__ = "episodes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    season_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_group: Mapped[str] = mapped_column(String(200), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    is_published: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    season: Mapped["Season"] = relationship("Season", back_populates="episodes")
    artworks: Mapped[list["Artwork"]] = relationship(
        "Artwork",
        back_populates="episode",
        cascade="all, delete-orphan",
        foreign_keys="Artwork.episode_id",
    )

    __table_args__ = (
        UniqueConstraint("content_group", "language", name="uq_content_group_language"),
        Index("ix_episodes_title", "title"),
        Index("ix_episodes_content_group", "content_group"),
        Index("ix_episodes_language", "language"),
        Index("ix_episodes_season_id", "season_id"),
    )
