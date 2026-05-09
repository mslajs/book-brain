# Book Brain — Router & Retriever

## router.py

The router's job is to look at the user's question and the full list of books in `config.py`, and return a list of namespaces that are meaningfully relevant. It uses a Claude API call to do this.

### What to build

A single function:

```python
def get_relevant_books(question: str, chat_history: list[dict]) -> list[str]:
    """
    Returns a list of Pinecone namespaces for books relevant to the question.
    chat_history is a list of {"role": "user"/"assistant", "content": "..."} dicts.
    """
```

### How it works

1. Build a prompt that includes:
   - The user's current question
   - The last 3 exchanges of chat history (for context — the question might reference something said earlier)
   - The full book list from `config.py`, formatted as: `namespace | title | author | topics`
2. Send to Claude using `claude-haiku-4-5-20251001` — this is a routing call, not a synthesis call, so use the fastest/cheapest model
3. Ask Claude to return a JSON array of namespace strings — nothing else
4. Parse and return the array

### Router prompt (use this exactly)

```
You are a relevance router for a personal book library assistant.

The user has asked:
"{question}"

Recent conversation context:
{last_3_exchanges}

The library contains these books:
{book_list_formatted}

Your job: return a JSON array of namespace strings for every book that contains knowledge meaningfully relevant to the user's question. Be inclusive — if a book has even a moderately useful perspective, include it. Only exclude books that are clearly unrelated.

Return ONLY a valid JSON array of namespace strings. No explanation. No markdown. Example:
["radical-candor", "high-output-management", "the-managers-path"]
```

### Parsing

- Strip any markdown formatting (` ```json `) before parsing
- If parsing fails, log the error and return all namespaces as a safe fallback (so the app never breaks)
- If Claude returns an empty array, return an empty list — do NOT fall back to all namespaces. An empty result means nothing is relevant; querying every book would flood the orchestrator with noise. The orchestrator already handles empty passages with a graceful "not in your library" message.

### Notes

- Do not use `claude-sonnet-4-6` here — haiku is fast and sufficient for a routing decision
- The router should complete in under 2 seconds
- Always return a list, never raise an exception to the caller

---

## retriever.py

The retriever's job is to query Pinecone for relevant passages from a list of book namespaces, in parallel.

### What to build

A single function:

```python
def retrieve_passages(question: str, namespaces: list[str], top_k: int = 5) -> list[dict]:
    """
    Queries each namespace in parallel and returns all retrieved passages.
    Each passage is a dict with: title, author, namespace, text, score.
    """
```

### How it works

1. Embed the user's question using OpenAI `text-embedding-3-small`
2. For each namespace in the list, query Pinecone with:
   - The question embedding
   - `top_k=5` (return top 5 most relevant chunks per book)
   - Filter by namespace
3. Run all namespace queries in parallel using `concurrent.futures.ThreadPoolExecutor`
4. Collect all results, flatten into a single list
5. Sort by relevance score descending
6. Return the list

### Return format

Each item in the returned list:

```python
{
    "title": "Radical Candor",
    "author": "Kim Scott",
    "namespace": "radical-candor",
    "text": "The actual chunk text goes here...",
    "score": 0.87
}
```

### Filtering low-quality results

- Drop any passage with a score below `0.70` — these are likely noise
- If filtering leaves a namespace with zero passages, that's fine — just don't include empty results

### Notes

- Use `top_k=5` per book as the default — this is enough to get specific insights without overwhelming the orchestrator
- Parallel execution is important here — if the router selects 10 books, sequential queries would be too slow
- The text comes from the `text` field stored in Pinecone metadata during ingestion
- Do not re-rank results across books — preserve per-book grouping so the orchestrator can attribute insights correctly

### Dependencies needed

```
openai
pinecone
python-dotenv
```
