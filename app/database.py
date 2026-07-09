from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase,sessionmaker
from core.config import settings

DATABASE_URL = settings.DATABASE_URL

engine = create_engine(DATABASE_URL)

Session = sessionmaker(
    autocommit = False,
    autoflush= False,
    bind=engine
)

class Base(DeclarativeBase):
    pass


def get_db():
    session=Session()
    try:
        yield session
    finally:
        session.close()