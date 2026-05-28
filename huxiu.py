import logging
from datetime import datetime

import requests
from bs4 import BeautifulSoup, Tag

from db import insert_article, update_article_translation
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


def parse_huxiu_article(url: str) -> dict:
    resp = requests.get(url, headers=HEADERS, proxies=PROXIES, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")

    title_el = soup.select_one("h1.article__title")
    title = title_el.get_text(strip=True) if title_el else ""

    time_el = soup.select_one("span.article__time")
    raw_date = time_el.get_text(strip=True) if time_el else ""
    source_date = datetime.strptime(raw_date, "%Y-%m-%d %H:%M") if raw_date else None

    content_el = soup.select_one("div.article__content")
    blocks = parse_article_blocks(content_el) if content_el else []

    return {
        "title": title,
        "blocks": blocks,
        "source_url": url,
        "source_date": source_date,
        "published_at": source_date or datetime.utcnow(),
    }


def main():
    url = "https://www.huxiu.com/article/4862493.html"
    data = parse_huxiu_article(url)
    text_html = blocks_to_html(data["blocks"])

    article = insert_article(
        title=data["title"],
        text=text_html,
        source_id=SOURCE_ID,
        source_name=SOURCE_NAME,
        source_url=data["source_url"],
        published_at=data["published_at"],
    )
    logger.info("Inserted article id=%d title=%s", article.id, article.title)

    title_ru, text_html_ru = translate_article(article.title, data["blocks"])
    article = update_article_translation(article, title_ru, text_html_ru)
    logger.info("Translated article id=%d", article.id)


if __name__ == "__main__":
    main()
