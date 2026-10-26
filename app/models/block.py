from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Block(Base):
    """Blocked users can't see or interact with the blocker, and vice versa."""

    __tablename__ = "blocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    blocker_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    blocked_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    blocked = relationship("User", foreign_keys=[blocked_id])

    __table_args__ = (
        UniqueConstraint("blocker_id", "blocked_id", name="uq_blocker_blocked"),
        CheckConstraint("blocker_id != blocked_id", name="ck_no_self_block"),
    )


class Mute(Base):
    """Muted users' posts, comments and notifications are hidden from the muter only."""

    __tablename__ = "mutes"

    id: Mapped[int] = mapped_column(primary_key=True)
    muter_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    muted_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    muted = relationship("User", foreign_keys=[muted_id])

    __table_args__ = (
        UniqueConstraint("muter_id", "muted_id", name="uq_muter_muted"),
        CheckConstraint("muter_id != muted_id", name="ck_no_self_mute"),
    )
