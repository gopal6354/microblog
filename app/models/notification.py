from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class NotificationType(str, Enum):
    COMMENT = "comment"
    FOLLOW = "follow"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipient_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[NotificationType] = mapped_column(
        SQLEnum(NotificationType), nullable=False
    )
    blog_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("blogs.id", ondelete="CASCADE"), nullable=True
    )
    # the source row; deleting it (uncomment / unfollow) removes the notification
    comment_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"), nullable=True
    )
    follow_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("follows.id", ondelete="CASCADE"), nullable=True
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    recipient = relationship(
        "User", foreign_keys=[recipient_id], back_populates="notifications"
    )
    actor = relationship(
        "User", foreign_keys=[actor_id], back_populates="sent_notifications"
    )
    blog = relationship("Blog", back_populates="notifications")
    comment = relationship("Comment", back_populates="notifications")
    follow = relationship("Follow", back_populates="notifications")
