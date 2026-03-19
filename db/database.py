"""Datenbank-Verbindung und Session-Management."""
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

import config

logger = logging.getLogger(__name__)

engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in config.DATABASE_URL else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def _migrate_columns():
    """Prüft ob alle Model-Spalten in der DB existieren und fügt fehlende hinzu (SQLite)."""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue  # Neue Tabelle – wird von create_all erstellt

        existing_cols = {c["name"] for c in inspector.get_columns(table.name)}

        for col in table.columns:
            if col.name not in existing_cols:
                col_type = col.type.compile(engine.dialect)
                with engine.begin() as conn:
                    conn.execute(text(
                        f"ALTER TABLE {table.name} ADD COLUMN {col.name} {col_type}"
                    ))
                logger.info(f"Migration: Spalte '{col.name}' zu Tabelle '{table.name}' hinzugefügt")


def init_db():
    """Erstellt alle Tabellen und migriert fehlende Spalten."""
    from db.models import Benutzer, Gebaeude, Zaehler, Ablesung, ZaehlerFoto, Bericht, Ordner
    Base.metadata.create_all(bind=engine)
    _migrate_columns()


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
