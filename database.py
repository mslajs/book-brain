import logging
import os

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

logger = logging.getLogger(__name__)

_client: Client | None = None

try:
    _client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
except Exception as e:
    logger.warning(f"Supabase unavailable — chat history will not be persisted: {e}")


def create_session(first_question: str) -> str:
    """Creates a new session. Returns the session UUID."""
    if _client is None:
        return ""
    try:
        title = first_question[:60]
        response = _client.table("sessions").insert({"title": title}).execute()
        return response.data[0]["id"]
    except Exception as e:
        logger.warning(f"create_session failed: {e}")
        return ""


def save_message(session_id: str, role: str, content: str) -> None:
    """Saves a single message to the messages table."""
    if _client is None or not session_id:
        return
    try:
        _client.table("messages").insert({
            "session_id": session_id,
            "role": role,
            "content": content,
        }).execute()
    except Exception as e:
        logger.warning(f"save_message failed: {e}")


def get_chat_history(session_id: str) -> list[dict]:
    """
    Returns all messages for a session as a list of dicts.
    Format: [{"role": "user"/"assistant", "content": "..."}]
    Ordered by created_at ascending.
    """
    if _client is None or not session_id:
        return []
    try:
        response = (
            _client.table("messages")
            .select("role, content")
            .eq("session_id", session_id)
            .order("created_at", desc=False)
            .execute()
        )
        return [{"role": m["role"], "content": m["content"]} for m in response.data]
    except Exception as e:
        logger.warning(f"get_chat_history failed: {e}")
        return []


def delete_session(session_id: str) -> None:
    """Deletes a session and all its messages (cascade on delete)."""
    if _client is None or not session_id:
        return
    try:
        _client.table("sessions").delete().eq("id", session_id).execute()
    except Exception as e:
        logger.warning(f"delete_session failed: {e}")


def get_all_sessions() -> list[dict]:
    """
    Returns all sessions ordered by created_at descending.
    Format: [{"id": "uuid", "title": "...", "created_at": "..."}]
    Used to populate the sidebar session list.
    """
    if _client is None:
        return []
    try:
        response = (
            _client.table("sessions")
            .select("id, title, created_at")
            .order("created_at", desc=True)
            .execute()
        )
        return response.data
    except Exception as e:
        logger.warning(f"get_all_sessions failed: {e}")
        return []
