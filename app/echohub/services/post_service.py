from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Tag
from utils.text import extract_hashtags

MAX_POST_WORDS = 280
MAX_SCHEDULE_AHEAD = timedelta(days=365)


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


def parse_schedule(value: str | None, tz_offset: int | None):
    """Turn a datetime-local value and the browser's UTC offset into naive UTC.

    Returns (datetime | None, error | None). `tz_offset` is JavaScript's
    getTimezoneOffset(): minutes to add to local time to get UTC.
    """
    if not value:
        return None, None
    try:
        local = datetime.fromisoformat(value)
    except ValueError:
        return None, "Invalid schedule time."
    if local.tzinfo is not None:
        return None, "Invalid schedule time."

    scheduled = local + timedelta(minutes=tz_offset or 0)
    now = datetime.utcnow()
    if scheduled <= now:
        return None, "Scheduled time must be in the future."
    if scheduled > now + MAX_SCHEDULE_AHEAD:
        return None, "Posts can be scheduled at most a year ahead."
    return scheduled, None
