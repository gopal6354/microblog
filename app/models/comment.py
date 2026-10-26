from datetime import datetime
from typing import Optional

from sqlalchemy import Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    blog_id: Mapped[int] = mapped_column(
        ForeignKey("blogs.id", ondelete="CASCADE"), nullable=False
    )
    # replies are one level deep; a reply to a reply attaches to the top comment
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"), nullable=True, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    # only set when the comment is edited
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user = relationship("User", back_populates="comments")
    blog = relationship("Blog", back_populates="comments")
    notifications = relationship(
        "Notification", back_populates="comment", cascade="all,delete-orphan"
    )
    parent = relationship("Comment", remote_side=[id], back_populates="replies")
    replies = relationship(
        "Comment", back_populates="parent", cascade="all,delete-orphan"
    )
