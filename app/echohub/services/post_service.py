from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Tag
from utils.text import extract_hashtags

MAX_POST_WORDS = 280


def post_content_error(content: str):
    if not content:
        return "Post content cannot be empty."
    if len(content.split()) > MAX_POST_WORDS:
        return f"Your post cannot exceed {MAX_POST_WORDS} words."
    return None


def sync_tags(session: Session, blog):
    names = extract_hashtags(blog.content)
    existing = {
        tag.name: tag
        for tag in session.scalars(select(Tag).where(Tag.name.in_(names))).all()
    }
    blog.tags = [existing.get(name) or Tag(name=name) for name in names]
