# How to use these files with Claude Code

## What these files are

This folder contains a complete specification for the Book Brain app — a personal RAG-powered book library assistant. The files are written specifically to be fed to Claude Code as context for vibe coding the project.

There are 5 spec files:

| File | What it covers |
|---|---|
| `00-project-overview.md` | Architecture, decisions, file structure, build order |
| `01-config-and-ingestion.md` | `config.py` and `ingest.py` |
| `02-router-and-retriever.md` | `router.py` and `retriever.py` |
| `03-orchestrator-and-database.md` | `orchestrator.py` and `database.py` |
| `04-streamlit-ui.md` | `app.py` and deployment |

---

## Recommended Claude Code session flow

### Session 1 — Project setup + ingestion

Feed Claude Code all 5 files at once as context, then say:

> "Read all the spec files I've provided. Start by scaffolding the full project structure, then build `config.py` and `ingest.py` exactly as specified. Add a couple of placeholder books to config. Don't build anything else yet."

Once it's done, test ingestion manually:
```bash
python ingest.py --namespace radical-candor
```

---

### Session 2 — Router and retriever

> "Build `router.py` and `retriever.py` as specified. Then write a small test script `test_retrieval.py` that asks a sample question, runs it through the router and retriever, and prints the results so I can verify it's working."

Test it:
```bash
python test_retrieval.py
```

---

### Session 3 — Orchestrator and database

> "Build `orchestrator.py` and `database.py` as specified. Create the Supabase tables using the SQL in the spec. Then extend `test_retrieval.py` to also call the orchestrator and print the final answer."

---

### Session 4 — UI

> "Build `app.py` as specified. Wire together all the modules. Make sure error handling is in place. The app should be runnable with `streamlit run app.py`."

Test locally:
```bash
streamlit run app.py
```

---

### Session 5 — Deploy

> "Help me deploy this to Streamlit Community Cloud. Generate the `.gitignore`, check `requirements.txt` is complete, and walk me through pushing to GitHub and connecting to Streamlit Cloud."

---

## Tips for vibe coding sessions

- **One module at a time** — don't ask Claude Code to build everything in one go. The spec is already broken into the right chunks.
- **Test before moving on** — each session ends with a working, testable piece. Don't proceed to the next until the current one works.
- **When something breaks**, paste the error into Claude Code and say "fix this" — don't try to debug it yourself first.
- **Adding a new book** is always two steps: add it to `config.py`, then run `ingest.py`. Remind Claude Code of this if it forgets.
- **The spec files are the source of truth** — if Claude Code suggests something that contradicts the spec, refer back to the spec and ask it to follow it.

---

## After the app is running — adding books

For each new book:

1. Get a clean, text-based PDF (not scanned)
2. Name it `books/{namespace}.pdf` where namespace matches what you add to `config.py`
3. Add the book entry to `BOOKS` in `config.py`
4. Run: `python ingest.py --namespace your-namespace`
5. The book is immediately available in the app — no restart needed

---

## Costs to expect

| Item | Cost |
|---|---|
| Pinecone free tier | $0 (up to ~30 books) |
| Supabase free tier | $0 |
| Streamlit Community Cloud | $0 |
| OpenAI embeddings (one-time per book) | ~$0.01 per book |
| Claude router calls | ~$0.001 per question |
| Claude orchestrator calls | ~$0.01–0.05 per question |
| **Estimated monthly cost at 50 questions/day** | **~$2–5/month** |
