# Book Brain — Project Overview

## What we're building

A personal AI assistant that answers product, leadership, and work questions by drawing on a personal library of books. Each book is stored as a searchable vector index. When a question is asked, a router identifies all relevant books, retrieves the most pertinent passages from each, and an orchestrator (Claude) synthesizes everything into one coherent answer — crediting each book by name.

This is a personal tool for one user. It is not a multi-tenant SaaS app. Keep everything simple, readable, and easy to modify.

---

## Core user flow

1. User types a question in a chat UI (e.g. "How should I handle a consistently underperforming team member?")
2. A router call to Claude identifies which books in the library are relevant to the question — no hard cap, include everything with meaningful relevance
3. The relevant books' vector stores are queried in parallel to retrieve the most useful passages
4. All retrieved passages + the full chat history are sent to Claude as orchestrator
5. Claude returns a synthesized answer that explicitly names which book each insight comes from
6. The answer appears in the chat UI; the exchange is saved to the database for future context

---

## Key design decisions

- **One Pinecone namespace per book** — not one index per book. All books live in a single Pinecone index, separated by namespace (e.g. `radical-candor`, `high-output-management`). This stays within the free tier and is easier to manage.
- **Router is inclusive, not restrictive** — the router prompt asks Claude to return all books with meaningful relevance. For a broad question this might be 10+ books; for a narrow one, 3. There is no artificial cap.
- **Chunking strategy matters** — books are chunked at ~400 tokens with 50-token overlap. This gives specific, citable passages rather than vague summaries.
- **Chat history is always included** — the full conversation history for the current session is passed to the orchestrator so answers can reference what was said earlier.
- **Sessions are persisted in Supabase** — so the user can return to past conversations.

---

## Tech stack

| Layer | Tool | Why |
|---|---|---|
| UI | Streamlit | Built-in chat components, trivial to deploy |
| Hosting | Streamlit Community Cloud | Free, deploys from GitHub |
| Vector DB | Pinecone (free tier) | Managed, persistent, easy Python SDK |
| App DB | Supabase (free tier) | Postgres for chat history and session management |
| Embeddings | `text-embedding-3-small` (OpenAI) | Cheap, high quality, widely supported |
| Router | Claude API (`claude-haiku-4-5-20251001`) | Fast, cheap — routing only needs classification |
| Orchestrator | Claude API (`claude-sonnet-4-6`) | Best reasoning for synthesis tasks |
| Ingestion script | Python (local) | Run once per book, not part of the app |

---

## Project file structure

```
book-brain/
├── app.py                  # Streamlit app — main entry point
├── router.py               # Router logic — picks relevant books
├── retriever.py            # Pinecone query logic
├── orchestrator.py         # Claude synthesis call
├── database.py             # Supabase chat history read/write
├── ingest.py               # One-off script: PDF → Pinecone
├── config.py               # Book registry (title, author, namespace)
├── requirements.txt
├── .env                    # API keys (never commit this)
└── books/                  # Local PDFs (never commit these)
    ├── radical-candor.pdf
    ├── high-output-management.pdf
    └── ...
```

---

## Environment variables required

```
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
PINECONE_API_KEY=
PINECONE_INDEX_NAME=book-brain
SUPABASE_URL=
SUPABASE_KEY=
```

---

## What to build first (order matters)

1. `config.py` — the book registry
2. `ingest.py` — get books into Pinecone before anything else
3. `retriever.py` — confirm retrieval works
4. `router.py` — confirm routing works
5. `orchestrator.py` — confirm synthesis works
6. `database.py` — add persistence
7. `app.py` — wire everything into the UI

Test each module individually before wiring them together.
