import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Boolean, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class Show(Base):
    __tablename__ = "shows"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    synopsis: Mapped[str] = mapped_column(Text, nullable=True, default="")
    category: Mapped[str] = mapped_column(String(100), nullable=True)
    section: Mapped[str] = mapped_column(String(100), nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    seasons: Mapped[list["Season"]] = relationship(
        "Season", back_populates="show", cascade="all, delete-orphan",
        order_by="Season.season_number"
    )
    artworks: Mapped[list["Artwork"]] = relationship(
        "Artwork",
        back_populates="show",
        cascade="all, delete-orphan",
        foreign_keys="Artwork.show_id",
    )

    __table_args__ = (
        Index("ix_shows_title", "title"),
        Index("ix_shows_section", "section"),
        Index("ix_shows_category", "category"),
        Index("ix_shows_is_published", "is_published"),
    )
