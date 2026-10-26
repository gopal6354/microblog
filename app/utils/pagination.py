import math
from dataclasses import dataclass

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


@dataclass
class Page:
    items: list
    page: int
    per_page: int
    total: int

    @property
    def total_pages(self):
        return max(1, math.ceil(self.total / self.per_page))

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.total_pages

    def page_numbers(self, window: int = 2):
        # first, last and a window around the current page; None marks a gap
        pages = []
        for p in range(1, self.total_pages + 1):
            if p in (1, self.total_pages) or abs(p - self.page) <= window:
                pages.append(p)
            elif pages and pages[-1] is not None:
                pages.append(None)
        return pages


def paginate(session: Session, query: Select, page: int, per_page: int) -> Page:
    total = session.scalar(
        select(func.count()).select_from(query.order_by(None).subquery())
    )
    # clamp past-the-end pages to the last page instead of showing an empty list
    page = min(max(page, 1), max(1, math.ceil(total / per_page)))
    items = session.scalars(query.limit(per_page).offset((page - 1) * per_page)).all()
    return Page(items=items, page=page, per_page=per_page, total=total)
