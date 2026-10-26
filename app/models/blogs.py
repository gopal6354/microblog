from datetime import datetime
from typing import Optional

from sqlalchemy import Text, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Blog(Base):
    __tablename__ = "blogs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    image: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    video: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    is_hidden: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
    )
    hidden_by_suspension: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
    )
    user = relationship("User", back_populates="blogs")
    likes = relationship("Like", back_populates="blog", cascade="all,delete-orphan")
    reports = relationship("Report", back_populates="blog", cascade="all,delete-orphan")
    comments = relationship(
        "Comment",
        back_populates="blog",
        cascade="all,delete-orphan",
        order_by="Comment.created_at",
    )
    notifications = relationship(
        "Notification", back_populates="blog", cascade="all,delete-orphan"
    )
