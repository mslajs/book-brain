import streamlit as st
from datetime import datetime, timezone

from router import get_relevant_books
from retriever import retrieve_passages
from orchestrator import synthesize
from database import create_session, save_message, get_chat_history, get_all_sessions, delete_session


# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(page_title="Book Brain", layout="centered")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _relative_date(created_at_str: str) -> str:
    try:
        created = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - created
        if delta.days == 0:
            return "Today"
        elif delta.days == 1:
            return "Yesterday"
        return f"{delta.days} days ago"
    except Exception:
        return ""


# ── Session state init ────────────────────────────────────────────────────────

if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "sessions" not in st.session_state:
    st.session_state.sessions = get_all_sessions()
if "last_sources" not in st.session_state:
    st.session_state.last_sources = []


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("Book Brain")

    if st.button("＋  New conversation", use_container_width=True, type="primary"):
        st.session_state.session_id = None
        st.session_state.messages = []
        st.session_state.last_sources = []
        st.rerun()

    st.divider()

    for session in st.session_state.sessions:
        title = session.get("title") or "Untitled"
        date = _relative_date(session.get("created_at", ""))
        truncated = title[:45] + ("..." if len(title) > 45 else "")
        label = f"{truncated}\n{date}" if date else truncated

        col1, col2 = st.columns([5, 1])
        with col1:
            if st.button(label, key=f"session_{session['id']}", use_container_width=True):
                st.session_state.session_id = session["id"]
                st.session_state.messages = get_chat_history(session["id"])
                st.session_state.last_sources = []
                st.rerun()
        with col2:
            if st.button("🗑", key=f"delete_{session['id']}"):
                delete_session(session["id"])
                if st.session_state.session_id == session["id"]:
                    st.session_state.session_id = None
                    st.session_state.messages = []
                    st.session_state.last_sources = []
                st.session_state.sessions = get_all_sessions()
                st.rerun()


# ── Main chat area ────────────────────────────────────────────────────────────

if not st.session_state.messages:
    st.markdown(
        "<br><br><br>"
        "<p style='text-align:center; color:#888; font-size:1.05rem;'>"
        "Ask a question to get started.<br>"
        "Your library will be searched for the most relevant insights."
        "</p>",
        unsafe_allow_html=True,
    )
else:
    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

        # Sources expander below the last assistant message only
        is_last = i == len(st.session_state.messages) - 1
        if msg["role"] == "assistant" and is_last and st.session_state.last_sources:
            n = len(st.session_state.last_sources)
            label = f"Sources consulted ({n} {'book' if n == 1 else 'books'})"
            with st.expander(label):
                for s in st.session_state.last_sources:
                    st.markdown(f"• **{s['title']}** — {s['author']}")


# ── Chat input ────────────────────────────────────────────────────────────────

if prompt := st.chat_input("Ask your library..."):
    is_first = not st.session_state.session_id
    # Snapshot history before this message — passed to router and orchestrator
    chat_history = list(st.session_state.messages)

    if is_first:
        session_id = create_session(prompt)
        st.session_state.session_id = session_id
    else:
        session_id = st.session_state.session_id

    save_message(session_id, "user", prompt)

    # Show user message immediately, before the spinner starts
    with st.chat_message("user"):
        st.write(prompt)

    with st.spinner("Searching your library..."):
        try:
            namespaces = get_relevant_books(prompt, chat_history)
            print(f"[router] namespaces selected: {namespaces}")
            passages = retrieve_passages(prompt, namespaces)
            print(f"[retriever] passages returned: {len(passages)} (threshold 0.55)")
            for p in passages:
                print(f"  [{p['score']:.3f}] {p['namespace']} — {p['text'][:80]!r}")
        except Exception:
            st.error("Something went wrong searching your library. Please try again.")
            st.stop()

        print(f"[orchestrator] sending {len(passages)} passages for: {prompt!r}")
        try:
            answer = synthesize(prompt, passages, chat_history)
        except Exception:
            st.error("Something went wrong searching your library. Please try again.")
            st.stop()

    # Deduplicated source list ordered by first appearance
    seen: set[str] = set()
    sources = []
    for p in passages:
        if p["namespace"] not in seen:
            seen.add(p["namespace"])
            sources.append({"title": p["title"], "author": p["author"]})

    with st.chat_message("assistant"):
        st.write(answer)

    if sources:
        n = len(sources)
        with st.expander(f"Sources consulted ({n} {'book' if n == 1 else 'books'})"):
            for s in sources:
                st.markdown(f"• **{s['title']}** — {s['author']}")

    # Persist and update state
    save_message(session_id, "assistant", answer)
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.session_state.last_sources = sources
    st.session_state.sessions = get_all_sessions()

    st.rerun()
