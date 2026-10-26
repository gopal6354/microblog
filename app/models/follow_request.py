from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class FollowRequest(Base):
    """Pending follow of a private account; approving it creates a Follow."""

    __tablename__ = "follow_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    requester_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    target_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    requester = relationship("User", foreign_keys=[requester_id])

    notifications = relationship(
        "Notification", back_populates="follow_request", cascade="all,delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("requester_id", "target_id", name="uq_requester_target"),
        CheckConstraint("requester_id != target_id", name="ck_no_self_request"),
    )
