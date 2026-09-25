"""ORM models: users, saved words (SRS cards), and the review log.

All datetimes are naive UTC — SQLite stores and compares them
consistently, and `iso()` serializes them back with an explicit Z.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat(timespec="seconds") + "Z"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(), default=utcnow)

    words: Mapped[list["Word"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Word(Base):
    __tablename__ = "words"
    __table_args__ = (
        UniqueConstraint("user_id", "native_lang", "target_lang", "text", name="uq_user_word"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    # content snapshot taken from the analyze pipeline at save time
    text: Mapped[str] = mapped_column(String(255))
    translated: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approximation: Mapped[str] = mapped_column(String(255))
    expected_ipa: Mapped[str] = mapped_column(String(255))
    native_lang: Mapped[str] = mapped_column(String(20))
    target_lang: Mapped[str] = mapped_column(String(20))
    missing_sounds: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(), default=utcnow)

    # SM-2 scheduling state
    state: Mapped[str] = mapped_column(String(10), default="new")  # new | learning | review
    ease: Mapped[float] = mapped_column(Float, default=2.5)
    interval_days: Mapped[float] = mapped_column(Float, default=0.0)
    reps: Mapped[int] = mapped_column(Integer, default=0)
    lapses: Mapped[int] = mapped_column(Integer, default=0)
    due_at: Mapped[datetime] = mapped_column(DateTime(), default=utcnow, index=True)
    last_review_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)

    user: Mapped["User"] = relationship(back_populates="words")
    reviews: Mapped[list["ReviewLog"]] = relationship(
        back_populates="word", cascade="all, delete-orphan"
    )


class ReviewLog(Base):
    __tablename__ = "review_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    word_id: Mapped[int] = mapped_column(ForeignKey("words.id"), index=True)
    rating: Mapped[str] = mapped_column(String(10))  # again | hard | good | easy
    was_new: Mapped[bool] = mapped_column(default=False)  # card's first ever review
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(), default=utcnow)
    interval_days: Mapped[float] = mapped_column(Float, default=0.0)
    ease: Mapped[float] = mapped_column(Float, default=2.5)
    state: Mapped[str] = mapped_column(String(10))

    word: Mapped["Word"] = relationship(back_populates="reviews")


class PronunciationSuggestion(Base):
    """A user-suggested approximate pronunciation, shared across the userbase.

    `word_text` and `suggested_text` are casefolded so that the community key
    (language pair + word) matches the way `save_word` deduplicates words.
    """

    __tablename__ = "pronunciation_suggestions"
    __table_args__ = (
        UniqueConstraint(
            "native_lang", "target_lang", "word_text", "suggested_text",
            name="uq_pron_suggestion",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    native_lang: Mapped[str] = mapped_column(String(20))
    target_lang: Mapped[str] = mapped_column(String(20))
    word_text: Mapped[str] = mapped_column(String(255), index=True)
    suggested_text: Mapped[str] = mapped_column(String(255))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # user ids sampled into the test group at creation time; the author always
    # sees their own suggestion regardless of this list
    audience: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(), default=utcnow)


class PronunciationVote(Base):
    """A user's thumbs up/down on a suggested pronunciation."""

    __tablename__ = "pronunciation_votes"
    __table_args__ = (
        UniqueConstraint("suggestion_id", "user_id", name="uq_pron_vote"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    suggestion_id: Mapped[int] = mapped_column(
        ForeignKey("pronunciation_suggestions.id"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    vote: Mapped[str] = mapped_column(String(4))  # up | down
    created_at: Mapped[datetime] = mapped_column(DateTime(), default=utcnow)


class PronunciationSystemVote(Base):
    """A user's thumbs up/down on the system-generated pronunciation of a word."""

    __tablename__ = "pronunciation_system_votes"
    __table_args__ = (
        UniqueConstraint(
            "native_lang", "target_lang", "word_text", "user_id",
            name="uq_pron_system_vote",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    native_lang: Mapped[str] = mapped_column(String(20))
    target_lang: Mapped[str] = mapped_column(String(20))
    word_text: Mapped[str] = mapped_column(String(255), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    vote: Mapped[str] = mapped_column(String(4))  # up | down
    created_at: Mapped[datetime] = mapped_column(DateTime(), default=utcnow)
