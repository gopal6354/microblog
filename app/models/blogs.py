from datetime import datetime
from typing import Optional

from sqlalchemy import Text, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models.tag import blog_tags


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
    # set for reposts, which have empty content and show the original post
    repost_of_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("blogs.id", ondelete="CASCADE"), nullable=True, index=True
    )
    is_draft: Mapped[bool] = mapped_column(default=False, nullable=False)
    # when the post went public; for drafts it is set again on publish
    published_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
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
    bookmarks = relationship(
        "Bookmark", back_populates="blog", cascade="all,delete-orphan"
    )
    tags = relationship("Tag", secondary=blog_tags, back_populates="blogs")
    repost_of = relationship("Blog", remote_side=[id], back_populates="reposts")
    reposts = relationship(
        "Blog", back_populates="repost_of", cascade="all,delete-orphan"
    )

    @property
    def is_plain_repost(self):
        return self.repost_of_id is not None and not self.content
