from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


blog_tags = Table(
    "blog_tags",
    Base.metadata,
    Column("blog_id", ForeignKey("blogs.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    # stored lowercase so #Python and #python are the same tag
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    blogs = relationship("Blog", secondary=blog_tags, back_populates="tags")
