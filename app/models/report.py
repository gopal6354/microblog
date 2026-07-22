from datetime import datetime
from typing import Optional
from enum import Enum
from sqlalchemy import (
    ForeignKey,
    Text,
    UniqueConstraint,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class ReportReason(str, Enum):
    SPAM = "Spam"
    HARASSMENT = "Harassment"
    HATE_SPEECH = "Hate Speech"
    COPYRIGHT = "Copyright"
    OTHER = "Other"


class ReportStatus(str, Enum):
    PENDING = "Pending"
    REVIEWED = "Reviewed"
    RESOLVED = "Resolved"
    DISMISSED = "Dismissed"


class Report(Base):
    __tablename__ = "reports"

    __table_args__ = (
        UniqueConstraint(
            "reporter_id",
            "blog_id",
            name="uq_reporter_id_blog",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    reporter_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    blog_id: Mapped[int] = mapped_column(
        ForeignKey("blogs.id", ondelete="CASCADE"),
        nullable=False,
    )

    reason: Mapped[ReportReason] = mapped_column(
        SQLEnum(ReportReason),
        default=ReportReason.SPAM,
        nullable=False,
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[ReportStatus] = mapped_column(
        SQLEnum(ReportStatus),
        default=ReportStatus.PENDING,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    reporter = relationship("User", back_populates="reports")
    blog = relationship("Blog", back_populates="reports")
