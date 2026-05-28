import os
import logging
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import DeclarativeBase, Session

logger = logging.getLogger(__name__)

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"].replace("postgres://", "postgresql://", 1)


class Base(DeclarativeBase):
    pass


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    title_translated = Column(String, nullable=True)
    text_translated = Column(Text, nullable=True)
    source_id = Column(Integer, nullable=False)
    source_name = Column(String, nullable=False)
    source_url = Column(String, nullable=False, unique=True)
    # source_date = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=False)


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(_engine)
    return _engine


def insert_article(
    title: str,
    text: str,
    source_id: int,
    source_name: str,
    source_url: str,
    published_at: datetime,
    # source_date: datetime | None = None,
    title_translated: str | None = None,
    text_translated: str | None = None,
) -> Article:
    engine = get_engine()
    with Session(engine, expire_on_commit=False) as session:
        existing = session.query(Article).filter_by(source_url=source_url).first()
        if existing is not None:
            logger.warning(
                "Article with source_url=%s already exists (id=%d). Updating.",
                source_url,
                existing.id,
            )
            existing.title = title
            existing.text = text
            existing.source_id = source_id
            existing.source_name = source_name
            # existing.source_date = source_date
            existing.published_at = published_at
            if title_translated is not None:
                existing.title_translated = title_translated
            if text_translated is not None:
                existing.text_translated = text_translated
            session.commit()
            return existing

        article = Article(
            title=title,
            text=text,
            title_translated=title_translated,
            text_translated=text_translated,
            source_id=source_id,
            source_name=source_name,
            source_url=source_url,
            # source_date=source_date,
            published_at=published_at,
        )
        session.add(article)
        session.commit()
        logger.info("Inserted article id=%d: %s", article.id, article.title)
        return article


def update_article_translation(article: Article, title_translated: str, text_translated: str) -> Article:
    engine = get_engine()
    with Session(engine, expire_on_commit=False) as session:
        merged = session.merge(article)
        merged.title_translated = title_translated
        merged.text_translated = text_translated
        session.commit()
        logger.info("Updated translation for article id=%d", merged.id)
        return merged
