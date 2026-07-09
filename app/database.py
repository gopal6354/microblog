from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase,sessionmaker

DATABASE_URL = "postgresql://gopal:gopal123@localhost:5432/fastapi_db"

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