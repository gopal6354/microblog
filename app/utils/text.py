import re
from urllib.parse import quote

from markupsafe import Markup, escape

# a tag or mention must start a word, so emails, "&#39;" entities and urls with
# fragments are not picked up
HASHTAG_RE = re.compile(r"(?<![\w&#])#(\w{1,50})")
MENTION_RE = re.compile(r"(?<![\w@])@(\w{1,50})")


def extract_hashtags(text: str | None) -> list[str]:
    """Unique lowercase tag names in the order they first appear."""
    return list(dict.fromkeys(tag.lower() for tag in HASHTAG_RE.findall(text or "")))


def extract_mentions(text: str | None) -> set[str]:
    return set(MENTION_RE.findall(text or ""))


def linkify(text: str | None) -> Markup:
    """Escape text, then turn #tags and @mentions into links."""
    escaped = str(escape(text or ""))
    escaped = HASHTAG_RE.sub(
        lambda m: f'<a href="/tag/{quote(m.group(1).lower())}" class="hashtag">#{m.group(1)}</a>',
        escaped,
    )
    escaped = MENTION_RE.sub(
        lambda m: f'<a href="/profile/{quote(m.group(1))}" class="mention">@{m.group(1)}</a>',
        escaped,
    )
    return Markup(escaped)
