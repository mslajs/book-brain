# Book Brain — Config & Ingestion

## config.py

This file is the single source of truth for the book library. Every book that has been ingested into Pinecone must have an entry here. The router uses this list to know what books exist and what they cover.

### What to build

A Python file containing a list of dictionaries. Each dictionary represents one book.

```python
BOOKS = [
    {
        "namespace": "high-output-management",   # Pinecone namespace — lowercase, hyphenated, no spaces
        "title": "High Output Management",
        "author": "Andy Grove",
        "topics": "management, 1:1s, performance reviews, OKRs, team productivity, engineering leadership"
    },
    {
        "namespace": "radical-candor",
        "title": "Radical Candor",
        "author": "Kim Scott",
        "topics": "feedback, difficult conversations, management, caring personally, challenging directly"
    },
    {
        "namespace": "the-managers-path",
        "title": "The Manager's Path",
        "author": "Camille Fournier",
        "topics": "engineering management, career ladders, tech lead, director, VP engineering"
    },
    # Add more books here as they are ingested
]
```

The `topics` field is a short comma-separated description used by the router to decide relevance. Make it honest and specific — don't just copy the subtitle.

---

## ingest.py

This is a local script run manually once per book. It is never called by the Streamlit app. Its job: read a PDF, chunk it, embed the chunks, and upsert them into Pinecone under the correct namespace.

### What to build

A command-line script that accepts a namespace as an argument:

```
python ingest.py --namespace radical-candor
```

It should:

1. Look up the namespace in `config.py` to confirm it exists
2. Find the corresponding PDF at `books/{namespace}.pdf`
3. Extract text from the PDF using `pypdf`
4. Split the text into chunks of ~400 tokens with 50-token overlap using `RecursiveCharacterTextSplitter.from_tiktoken_encoder` (not the default constructor — the default counts characters, not tokens)
5. Embed each chunk using OpenAI `text-embedding-3-small`
6. Upsert vectors into Pinecone in batches of 100 (the API limit per call) under the specified namespace
7. Print progress as it goes — number of chunks, batch progress, confirmation of upsert

### Chunking details

- Chunk size: 400 tokens
- Chunk overlap: 50 tokens
- Use `RecursiveCharacterTextSplitter.from_tiktoken_encoder(encoding_name="cl100k_base", chunk_size=400, chunk_overlap=50)` — this ensures sizes are measured in tokens, matching the embedding model's tokenizer
- Include metadata on each vector:
  - `namespace`: the book namespace
  - `title`: the book title
  - `author`: the book author
  - `chunk_index`: integer position of chunk in the book
  - `text`: the raw text of the chunk (stored in metadata for retrieval)

### Pinecone setup

- Use a single Pinecone index named `book-brain`
- Dimension: 1536 (matches `text-embedding-3-small`)
- Metric: cosine
- Create the index if it doesn't exist on first run
- Use namespaces to separate books within the index

### Error handling

- If the PDF file doesn't exist, print a clear error and exit
- If the namespace isn't in `config.py`, print a clear error and exit
- If Pinecone upsert fails, retry once before raising

### Dependencies needed

```
pypdf
langchain-text-splitters
tiktoken
openai
pinecone
python-dotenv
```

> These are ingest-only dependencies. Keep them in `requirements-ingest.txt`, not in `requirements.txt` — they don't need to be deployed to Streamlit Cloud.

### Example output when run

```
Found: Radical Candor by Kim Scott
Loading PDF: books/radical-candor.pdf
Extracted 312 pages
Split into 847 chunks
Embedding chunks... (this may take a minute)
Upserting to Pinecone namespace: radical-candor
Upserted 847 vectors
Done. radical-candor is ready to query.
```
