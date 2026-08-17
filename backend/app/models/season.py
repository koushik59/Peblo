import uuid
from datetime import datetime, timezone
from sqlalchemy import Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class Season(Base):
    __tablename__ = "seasons"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    show_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shows.id", ondelete="CASCADE"), nullable=False)
    season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    show: Mapped["Show"] = relationship("Show", back_populates="seasons")
    episodes: Mapped[list["Episode"]] = relationship(
        "Episode", back_populates="season", cascade="all, delete-orphan",
        order_by="Episode.title"
    )

    __table_args__ = (
        UniqueConstraint("show_id", "season_number", name="uq_show_season_number"),
    )
