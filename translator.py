import logging
import time

from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)

TARGET_LANG = "ru"

_translator = None


def get_translator():
    global _translator
    if _translator is None:
        _translator = GoogleTranslator(source="zh-CN", target=TARGET_LANG)
    return _translator


def translate_text(text: str, chunk_size: int = 1000) -> str:
    translator = get_translator()
    if len(text) <= chunk_size:
        return translator.translate(text)
    parts = []
    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        logger.debug("Translating chunk %d/%d (%d chars)", i // chunk_size + 1, (len(text) + chunk_size - 1) // chunk_size, len(chunk))
        translated = translator.translate(chunk)
        parts.append(translated)
    return "\n\n".join(parts)


def translate_blocks(blocks: list[tuple[str, str]]) -> list[tuple[str, str]]:
    total = len(blocks)
    translated = []
    for idx, (tag, text) in enumerate(blocks, 1):
        preview = text[:50].replace("\n", " ")
        logger.info("Translating block %d/%d [%s]: %s...", idx, total, tag, preview)
        t = translate_text(text)
        translated.append((tag, t))
        time.sleep(0.3)
    return translated


def blocks_to_html(blocks: list[tuple[str, str]]) -> str:
    return "\n".join(f"<{tag}>{text}</{tag}>" for tag, text in blocks)


def translate_article(title: str, blocks: list[tuple[str, str]]) -> tuple[str, str]:
    title_ru = translate_text(title)
    logger.info("Title translated: %s -> %s", title, title_ru)

    translated_blocks = translate_blocks(blocks)
    html_ru = blocks_to_html(translated_blocks)
    logger.info("Article translated: %d blocks", len(blocks))
    return title_ru, html_ru
