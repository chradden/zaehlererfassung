"""Datenbank-Verbindung und Session-Management."""
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

import config

engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in config.DATABASE_URL else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    """Erstellt alle Tabellen."""
    from db.models import Benutzer, Gebaeude, Zaehler, Ablesung, ZaehlerFoto, Bericht, Ordner
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_session():
    """Context Manager für Datenbank-Sessions."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
