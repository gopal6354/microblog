from database import Base
from sqlalchemy.orm import Mapped,mapped_column
from enum import Enum
from sqlalchemy import Enum as SQLEnum,String
from datetime import datetime
from typing import Optional

class RoleChoice(str,Enum):
    ADMIN = "admin"
    USER = "user"

class StatusChoice(str,Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class User(Base):
    __tablename__ = "users"
    id : Mapped[int] = mapped_column(primary_key=True,index=True)
    username : Mapped[str] = mapped_column(String(50), unique=True,nullable=False)
    email : Mapped[str] = mapped_column(String(255),unique=True,nullable=False)
    hashed_password : Mapped[str] = mapped_column(nullable=False)
    full_name : Mapped[Optional[str]] = mapped_column(String(50),nullable=True)
    role : Mapped[RoleChoice] = mapped_column(SQLEnum(RoleChoice),default=RoleChoice.USER) 
    status : Mapped[StatusChoice] = mapped_column(SQLEnum(StatusChoice),default=StatusChoice.INACTIVE) 
    bio : Mapped[Optional[str]] = mapped_column(String(150),nullable=True)
    profile_image : Mapped[Optional[str]] = mapped_column(nullable=True)
    created_at : Mapped[datetime] = mapped_column(default=datetime.utcnow)