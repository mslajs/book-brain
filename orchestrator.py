import os
from collections import defaultdict

import anthropic
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are a personal advisor with deep knowledge of the user's book library.
Your job is to answer the user's questions by drawing on specific insights from their books.

When answering:
- Always attribute insights to specific books by name and author
- If multiple books agree on a point, say so — it reinforces the idea
- If books offer different or conflicting perspectives, present both and let the user decide
- Be direct and practical — the user is asking because they have a real situation to handle
- Do not pad the answer — if three books have relevant things to say, cover all three concisely
- Write in a conversational tone, like a knowledgeable colleague, not a book report
- If the retrieved passages don't fully answer the question, say so honestly rather than hallucinating"""


def _format_passages(passages: list[dict]) -> str:
    # Group texts by book, preserving the per-book ordering from the retriever
    by_book: dict[str, dict] = {}
    for p in passages:
        ns = p["namespace"]
        if ns not in by_book:
            by_book[ns] = {"title": p["title"], "author": p["author"], "texts": []}
        by_book[ns]["texts"].append(p["text"])

    blocks = []
    for book in by_book.values():
        texts = "\n\n".join(book["texts"])
        blocks.append(f'From "{book["title"]}" by {book["author"]}:\n{texts}')

    return "\n\n---\n\n".join(blocks)


def synthesize(question: str, passages: list[dict], chat_history: list[dict]) -> str:
    """
    Sends question + retrieved passages + chat history to Claude.
    Returns the synthesized answer as a string.
    """
    if not passages:
        return (
            "I couldn't find relevant passages in your library for this question. "
            "Try rephrasing, or this topic may not be covered in your current books."
        )

    passages_block = _format_passages(passages)

    # Split the final user message into two content blocks so the passages
    # block can be cached independently of the (always-changing) question.
    final_user_message = {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": f"Here are the most relevant passages from your library:\n\n---\n\n{passages_block}\n\n---",
                "cache_control": {"type": "ephemeral"},
            },
            {
                "type": "text",
                "text": f"My question: {question}\n\nPlease synthesize these into a practical answer to my question.",
            },
        ],
    }

    messages = list(chat_history) + [final_user_message]

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=messages,
        extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
    )

    return response.content[0].text
