"""
SQLAlchemy 2.0 setup — синхронное подключение.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, scoped_session

DJ_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'sqlite:///' + os.path.join(DJ_DIR, 'instance', 'database.db')
)

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args={'check_same_thread': False} if 'sqlite' in DATABASE_URL else {},
)

SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency — сессия БД на запрос."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Создать таблицы."""
    import models  # noqa
    Base.metadata.create_all(bind=engine)
