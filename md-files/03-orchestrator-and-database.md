# Book Brain — Orchestrator & Database

## orchestrator.py

The orchestrator takes the retrieved passages from all relevant books plus the full chat history, and produces a single synthesized answer. This is the most important call in the system — use the best model and give it a strong prompt.

### What to build

A single function:

```python
def synthesize(question: str, passages: list[dict], chat_history: list[dict]) -> str:
    """
    Sends question + retrieved passages + chat history to Claude.
    Returns the synthesized answer as a string.
    """
```

### How it works

1. Format the retrieved passages into a structured block, grouped by book
2. Build the messages array with:
   - A system prompt (see below)
   - The full chat history as prior messages
   - A final user message containing the question and the retrieved passages
3. Call Claude `claude-sonnet-4-6` with the messages
4. Return the text content of the response

### System prompt (use this exactly)

```
You are a personal advisor with deep knowledge of the user's book library. 
Your job is to answer the user's questions by drawing on specific insights from their books.

When answering:
- Always attribute insights to specific books by name and author
- If multiple books agree on a point, say so — it reinforces the idea
- If books offer different or conflicting perspectives, present both and let the user decide
- Be direct and practical — the user is asking because they have a real situation to handle
- Do not pad the answer — if three books have relevant things to say, cover all three concisely
- Write in a conversational tone, like a knowledgeable colleague, not a book report
- If the retrieved passages don't fully answer the question, say so honestly rather than hallucinating
```

### Final user message format

```
My question: {question}

Here are the most relevant passages from your library:

---
{for each book}
From "{title}" by {author}:
{passage 1 text}
{passage 2 text}
...
---

Please synthesize these into a practical answer to my question.
```

### Notes

- Use `max_tokens=1500` — enough for a thorough answer without being verbose
- Pass `chat_history` as the conversation history so Claude has full context
- If `passages` is empty (router returned nothing, retriever found nothing), return a graceful message: "I couldn't find relevant passages in your library for this question. Try rephrasing, or this topic may not be covered in your current books."
- Do not stream the response for now — return the complete string
- **Use Anthropic prompt caching** on both the system prompt and the formatted passages block. Mark each with `"cache_control": {"type": "ephemeral"}`. The system prompt is static across all calls; the passages block is large and changes per question but not per token of the answer. Caching these two blocks meaningfully reduces cost and latency on longer sessions. See the Anthropic prompt caching docs for the exact message format.

---

## database.py

Handles all Supabase interactions for session and chat history management.

### Supabase schema to create

Run this SQL in the Supabase SQL editor to set up the tables:

```sql
create table sessions (
  id uuid primary key default gen_random_uuid(),
  created_at timestamp with time zone default now(),
  title text  -- first question of the session, truncated to 60 chars
);

create table messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references sessions(id) on delete cascade,
  role text not null,  -- 'user' or 'assistant'
  content text not null,
  created_at timestamp with time zone default now()
);

create index on messages(session_id);
```

### What to build

Four functions:

```python
def create_session(first_question: str) -> str:
    """Creates a new session. Returns the session UUID."""

def save_message(session_id: str, role: str, content: str) -> None:
    """Saves a single message to the messages table."""

def get_chat_history(session_id: str) -> list[dict]:
    """
    Returns all messages for a session as a list of dicts.
    Format: [{"role": "user"/"assistant", "content": "..."}]
    Ordered by created_at ascending.
    """

def get_all_sessions() -> list[dict]:
    """
    Returns all sessions ordered by created_at descending.
    Format: [{"id": "uuid", "title": "...", "created_at": "..."}]
    Used to populate the sidebar session list.
    """
```

### Notes

- Use the `supabase-py` client library
- All functions should handle exceptions gracefully — if Supabase is unavailable, the app should still work, just without persistence (log a warning, don't crash)
- `create_session` sets the title to the first 60 characters of the first question
- `get_chat_history` is called before every orchestrator call to include full context

### Dependencies needed

```
supabase
python-dotenv
```
