# Book Brain — Streamlit UI (app.py)

## What to build

A single `app.py` file that wires together all modules into a working chat interface. The UI has two areas: a sidebar for session management, and a main area for the chat.

---

## Layout

### Sidebar
- App title: "Book Brain"
- A "New conversation" button at the top
- A list of past sessions below it, each showing the session title (first question, truncated) and relative date
- Clicking a session loads that conversation into the main chat area
- A thin divider between the button and the session list

### Main area
- If no session is active: a centered welcome message ("Ask a question to get started. Your library will be searched for the most relevant insights.")
- If a session is active: the full chat history displayed using `st.chat_message`
- A chat input box pinned to the bottom: "Ask your library..."

---

## State management

Use `st.session_state` to track:

```python
st.session_state.session_id      # current session UUID or None
st.session_state.messages        # list of {"role", "content"} for display
st.session_state.sessions        # list of all sessions for the sidebar
```

---

## User interaction flow

### Starting a new conversation
1. User clicks "New conversation" or the app loads fresh
2. Set `session_id` to None, clear `messages`

### Sending a first message
1. User types a question and hits enter
2. Create a new session in Supabase with `create_session(question)`
3. Save the user message with `save_message(session_id, "user", question)`
4. Display the user message immediately with `st.chat_message("user")`
5. Show a spinner: "Searching your library..."
6. Call `get_relevant_books(question, [])` — empty history on first message
7. Call `retrieve_passages(question, relevant_namespaces)`
8. Call `synthesize(question, passages, [])` — empty history on first message
9. Save the assistant message with `save_message(session_id, "assistant", answer)`
10. Display the answer with `st.chat_message("assistant")`
11. Refresh the sidebar session list

### Sending a follow-up message
Same as above, but:
- Pass `get_chat_history(session_id)` as `chat_history` to router and orchestrator
- Do not create a new session

### Loading a past session
1. User clicks a session in the sidebar
2. Set `session_id` to the clicked session's UUID
3. Load messages with `get_chat_history(session_id)` and set `st.session_state.messages`
4. Rerender the chat

---

## Showing which books were used

After each assistant response, display a small expander below the message:

```
▶ Sources consulted (3 books)
  • Radical Candor — Kim Scott
  • High Output Management — Andy Grove
  • The Manager's Path — Camille Fournier
```

Store the list of consulted books in `st.session_state` temporarily (no need to persist to DB).

---

## Error handling in the UI

- If the router or retriever fails: show `st.error("Something went wrong searching your library. Please try again.")`
- If the orchestrator fails: same error message
- Never show a Python traceback to the user
- Always allow the user to try again

---

## requirements.txt

Deployed to Streamlit Cloud — app dependencies only:

```
streamlit
anthropic
openai
pinecone
supabase
python-dotenv
```

## requirements-ingest.txt

Local only — for running `ingest.py`. Install once with `pip install -r requirements-ingest.txt`:

```
pypdf
langchain-text-splitters
tiktoken
openai
pinecone
python-dotenv
```

> `pypdf`, `langchain-text-splitters`, and `tiktoken` are not needed by the deployed app. Keeping them out of `requirements.txt` speeds up Streamlit Cloud builds and avoids unnecessary dependencies in production.

---

## Streamlit Community Cloud deployment

Once the app works locally:

1. Push the project to a GitHub repository (do NOT commit `.env` or the `books/` folder — add both to `.gitignore`)
2. Go to share.streamlit.io and connect the GitHub repo
3. In the Streamlit Cloud dashboard, add all environment variables from `.env` under "Secrets"
4. Deploy — Streamlit will install `requirements.txt` automatically

The app will be available at `https://your-app-name.streamlit.app`

---

## .gitignore

Make sure this is in the project root:

```
.env
books/
__pycache__/
*.pyc
.DS_Store
```
