import logging
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Tag
from sqlalchemy import create_engine, text as sa_text

from db import get_engine, insert_article, update_article_translation
from translator import translate_article

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

SOURCE_ID = 1
SOURCE_NAME = "huxiu"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

PROXIES = {
    "http": "socks5h://111.0.0.1:1080",
    "https": "socks5h://111.0.0.1:1080",
}

SITEMAP_PATH = Path(__file__).parent / "huxiu" / "article_1.xml"


def parse_article_blocks(content_el: Tag) -> list[tuple[str, str]]:
    blocks = []
    for child in content_el.children:
        if not isinstance(child, Tag):
            continue
        if child.name == "p" and child.get("class") == ["img-center-box"]:
            continue
        text = child.get_text(strip=True)
        if not text:
            continue
        tag = "h2" if child.name == "h2" else "p"
        blocks.append((tag, text))
    return blocks


def blocks_to_html(blocks: list[tuple[str, str]]) -> str:
    return "\n".join(f"<{tag}>{text}</{tag}>" for tag, text in blocks)


def parse_huxiu_article(url: str) -> dict | None:
    try:
        resp = requests.get(url, headers=HEADERS, proxies=PROXIES, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error("Failed to fetch %s: %s", url, e)
        return None

    soup = BeautifulSoup(resp.text, "lxml")

    title_el = soup.select_one("h1.article__title")
    if not title_el:
        logger.warning("No title found at %s, skipping", url)
        return None
    title = title_el.get_text(strip=True)

    time_el = soup.select_one("span.article__time")
    raw_date = time_el.get_text(strip=True) if time_el else ""
    source_date = None
    if raw_date:
        try:
            source_date = datetime.strptime(raw_date, "%Y-%m-%d %H:%M")
        except ValueError:
            logger.warning("Could not parse date '%s' for %s", raw_date, url)

    content_el = soup.select_one("div.article__content")
    blocks = parse_article_blocks(content_el) if content_el else []

    img_el = soup.select_one("img.article-img")
    img_source_url = img_el.get("src") if img_el else None

    return {
        "title": title,
        "blocks": blocks,
        "source_url": url,
        "source_date": source_date,
        "img_source_url": img_source_url,
        "published_at": source_date or datetime.utcnow(),
    }


def load_sitemap_urls(path: Path) -> list[str]:
    tree = ET.parse(path)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = []
    for loc in tree.findall(".//sm:loc", ns):
        urls.append(loc.text.strip())
    logger.info("Loaded %d URLs from sitemap", len(urls))
    return urls


def get_article_status() -> dict[str, int]:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa_text("SELECT source_url, id, title_translated IS NOT NULL AS has_translation FROM articles")
        ).fetchall()
    return {row[0]: {"id": row[1], "translated": row[2]} for row in rows}


def process_article(url: str) -> bool:
    data = parse_huxiu_article(url)
    if data is None:
        logger.warning("Skipping %s due to parse error", url)
        return False

    text_html = blocks_to_html(data["blocks"])

    try:
        article = insert_article(
            title=data["title"],
            text=text_html,
            source_id=SOURCE_ID,
            source_name=SOURCE_NAME,
            source_url=data["source_url"],
            source_date=data["source_date"],
            img_source_url=data["img_source_url"],
            published_at=data["published_at"],
        )
    except Exception as e:
        logger.error("Failed to insert %s: %s", url, e)
        return False

    logger.info("Inserted article id=%d title=%s", article.id, article.title)

    if not data["blocks"]:
        logger.warning("No text blocks for %s, skipping translation", url)
        return True

    try:
        title_ru, text_html_ru = translate_article(article.title, data["blocks"])
        article = update_article_translation(article, title_ru, text_html_ru)
        logger.info("Translated article id=%d", article.id)
    except Exception as e:
        logger.error("Translation failed for %s: %s", url, e)
        return False

    time.sleep(0.5)
    return True


def main():
    status = get_article_status()
    logger.info("Found %d existing articles in database", len(status))

    urls = load_sitemap_urls(SITEMAP_PATH)

    to_process = []
    for u in urls:
        entry = status.get(u)
        if entry is None:
            to_process.append(u)
        elif not entry["translated"]:
            logger.info("Re-processing %s (id=%d, missing translation)", u, entry["id"])
            to_process.append(u)

    skipped = len(urls) - len(to_process)
    logger.info("URLs to process: %d (skipping %d already done)", len(to_process), skipped)

    for idx, url in enumerate(to_process, 1):
        logger.info("[%d/%d] Processing %s", idx, len(to_process), url)
        process_article(url)

    logger.info("Done processing %d articles", len(to_process))


if __name__ == "__main__":
    main()
