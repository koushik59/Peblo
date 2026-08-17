import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, ForeignKey, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class Artwork(Base):
    """
    Artwork can be associated with either a show or an episode.
    artwork_type: 'poster', 'banner', 'thumbnail'
    """
    __tablename__ = "artworks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    show_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("shows.id", ondelete="CASCADE"), nullable=True
    )
    episode_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"), nullable=True
    )
    artwork_type: Mapped[str] = mapped_column(String(20), nullable=False)  # poster, banner, thumbnail
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # in bytes
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    show: Mapped["Show | None"] = relationship(
        "Show", back_populates="artworks", foreign_keys=[show_id]
    )
    episode: Mapped["Episode | None"] = relationship(
        "Episode", back_populates="artworks", foreign_keys=[episode_id]
    )

    __table_args__ = (
        Index("ix_artworks_show_id", "show_id"),
        Index("ix_artworks_episode_id", "episode_id"),
        Index("ix_artworks_artwork_type", "artwork_type"),
    )
