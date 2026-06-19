import logging
from typing import Optional
from backend.ai.scheme_parser import get_gemini_client
from backend.config import settings

logger = logging.getLogger(__name__)

async def summarize_text(text: str, max_words: int = 100) -> str:
    """
    Summarizes raw text using Gemini.
    Falls back to simple truncation if Gemini is unavailable.
    """
    client = get_gemini_client()
    if client:
        try:
            logger.info("Summarizing text using Gemini...")
            prompt = f"Summarize this text in less than {max_words} words:\n\n{text}"
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config={
                    "temperature": 0.3
                }
            )
            if response.text:
                return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini summarization failed: {e}")

    # Fallback: simple text truncation
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "..."
