from database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum
from sqlalchemy import Enum as SQLEnum, String, DateTime, Boolean
from datetime import datetime
from typing import Optional


class RoleChoice(str, Enum):
    ADMIN = "admin"
    USER = "user"
    SUPER_ADMIN = "super_admin"


class StatusChoice(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    role: Mapped[RoleChoice] = mapped_column(
        SQLEnum(RoleChoice), default=RoleChoice.USER
    )
    city: Mapped[Optional[str]] = mapped_column(nullable=True)
    state: Mapped[Optional[str]] = mapped_column(nullable=True)
    status: Mapped[StatusChoice] = mapped_column(
        SQLEnum(StatusChoice), default=StatusChoice.INACTIVE
    )
    bio: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    profile_image: Mapped[Optional[str]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    otp: Mapped[str | None] = mapped_column(nullable=True)
    otp_expiry: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    otp_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    blogs = relationship("Blog", back_populates="user", cascade="all,delete-orphan")
    likes = relationship("Like", back_populates="user", cascade="all,delete-orphan")
    reports = relationship(
        "Report", back_populates="reporter", cascade="all,delete-orphan"
    )
