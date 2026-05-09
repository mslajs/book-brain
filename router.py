import json
import logging
import os

import anthropic
from dotenv import load_dotenv

from config import BOOKS

load_dotenv()

logger = logging.getLogger(__name__)


def _format_book_list() -> str:
    return "\n".join(
        f"{b['namespace']} | {b['title']} | {b['author']} | {b['topics']}"
        for b in BOOKS
    )


def _format_history(chat_history: list[dict]) -> str:
    if not chat_history:
        return "(none)"
    recent = chat_history[-6:]  # last 3 exchanges = last 6 messages
    return "\n".join(f"{m['role'].capitalize()}: {m['content']}" for m in recent)


def get_relevant_books(question: str, chat_history: list[dict]) -> list[str]:
    """
    Returns a list of Pinecone namespaces for books relevant to the question.
    chat_history is a list of {"role": "user"/"assistant", "content": "..."} dicts.
    """
    all_namespaces = [b["namespace"] for b in BOOKS]

    prompt = f"""You are a relevance router for a personal book library assistant.

The user has asked:
"{question}"

Recent conversation context:
{_format_history(chat_history)}

The library contains these books:
{_format_book_list()}

Your job: return a JSON array of namespace strings for every book that contains knowledge meaningfully relevant to the user's question.

Rules:
- Pay close attention to the topics field for each book — if the question touches on any of those topics, include the book.
- Be inclusive: if a book has even a moderately useful perspective, include it.
- Match on concepts, not just keywords. A question about "people problems", "team issues", or "accountability" should match a book whose topics include "team dynamics", "trust", or "accountability" — even if those exact words aren't in the question.
- Only exclude books whose topics are clearly unrelated to the question.

Return ONLY a valid JSON array of namespace strings. No explanation. No markdown. Example:
["radical-candor", "high-output-management", "the-managers-path"]"""

    try:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

        result = json.loads(raw)

        if not isinstance(result, list) or len(result) == 0:
            logger.info("Router returned empty array — no relevant books found.")
            return []

        # Only return namespaces that exist in config
        return [ns for ns in result if ns in all_namespaces]

    except Exception as e:
        logger.error(f"Router error: {e}. Falling back to all namespaces.")
        return all_namespaces
