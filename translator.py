import logging

from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)

_translator = None


def get_translator():
    global _translator
    if _translator is None:
        _translator = GoogleTranslator(source="zh-CN", target="ru")
    return _translator


def translate_text(text: str, chunk_size: int = 1000) -> str:
    translator = get_translator()
    if len(text) <= chunk_size:
        return translator.translate(text)
    parts = []
    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        translated = translator.translate(chunk)
        parts.append(translated)
    return "\n\n".join(parts)


def translate_article(title: str, text: str) -> tuple[str, str]:
    title_en = translate_text(title)
    logger.info("Title translated: %s -> %s", title, title_en)
    text_en = translate_text(text)
    logger.info("Text translated (%d chars)", len(text))
    return title_en, text_en
