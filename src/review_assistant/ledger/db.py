"""The ledger table: one row per review, written through SQLAlchemy and migrated with Alembic."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import DateTime, Integer, String, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from review_assistant.log import fields, get_logger

log = get_logger("ledger")


class Base(DeclarativeBase):
    """The declarative base for the ledger's tables."""


class Review(Base):
    """One review: who ran it, on what, and what it cost."""

    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    pull_request: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delivery: Mapped[str | None] = mapped_column(String(64), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    cents: Mapped[int] = mapped_column(Integer, nullable=False)


def repository_root() -> Path:
    """Find the repository root from this file; the migrations live beside the package."""
    return Path(__file__).resolve().parents[3]


def alembic_config(ledger_path: str | Path) -> AlembicConfig:
    """Build an Alembic config pointed at the repository's migrations and at one SQLite file."""
    config = AlembicConfig(str(repository_root() / "alembic.ini"))
    config.set_main_option("script_location", str(repository_root() / "alembic"))
    config.set_main_option("sqlalchemy.url", url_for(ledger_path))
    return config


def url_for(ledger_path: str | Path) -> str:
    """Make the SQLAlchemy URL for a ledger file."""
    return f"sqlite:///{Path(ledger_path).as_posix()}"


def connect(ledger_path: str | Path) -> Engine:
    """Open the ledger, migrating it to the current schema first."""
    command.upgrade(alembic_config(ledger_path), "head")
    return create_engine(url_for(ledger_path))


def record_review(
    engine: Engine,
    *,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cents: int,
    pull_request: int | None = None,
    delivery: str | None = None,
) -> Review:
    """Insert one row for a review and return it."""
    row = Review(
        created_at=datetime.now(UTC).replace(tzinfo=None),
        provider=provider,
        model=model,
        pull_request=pull_request,
        delivery=delivery,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cents=cents,
    )
    with Session(engine) as session:
        session.add(row)
        session.commit()
        session.refresh(row)
        session.expunge(row)
    log.info("row         %s", fields(pr=pull_request, cents=cents))
    return row


def row_for(engine: Engine, pull_request: int) -> Review | None:
    """Fetch the most recent ledger row for a pull request, or None."""
    with Session(engine) as session:
        statement = (
            select(Review).where(Review.pull_request == pull_request).order_by(Review.id.desc()).limit(1)
        )
        row = session.scalars(statement).first()
        if row is not None:
            session.expunge(row)
        return row


def rows(engine: Engine) -> list[Review]:
    """Every ledger row, oldest first."""
    with Session(engine) as session:
        found = list(session.scalars(select(Review).order_by(Review.id)).all())
        for row in found:
            session.expunge(row)
        return found
