import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

load_dotenv()

SCORE_THRESHOLD = 0.40


def _embed_question(question: str) -> list[float]:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.embeddings.create(model="text-embedding-3-small", input=question)
    return response.data[0].embedding


def _query_namespace(index, embedding: list[float], namespace: str, top_k: int) -> list[dict]:
    results = index.query(
        vector=embedding,
        top_k=top_k,
        namespace=namespace,
        include_metadata=True,
    )
    print(f"[pinecone] namespace='{namespace}' returned {len(results.matches)} matches")
    passages = []
    for match in results.matches:
        metadata = match.metadata or {}
        text = metadata.get("text", "")
        print(f"  score={match.score:.3f} has_text={bool(text)}")
        if match.score < SCORE_THRESHOLD:
            continue
        if not text:
            continue
        passages.append({
            "title": metadata.get("title", ""),
            "author": metadata.get("author", ""),
            "namespace": namespace,
            "text": text,
            "score": match.score,
        })
    return passages


def retrieve_passages(question: str, namespaces: list[str], top_k: int = 5) -> list[dict]:
    """
    Queries each namespace in parallel and returns all retrieved passages.
    Each passage is a dict with: title, author, namespace, text, score.
    """
    if not namespaces:
        return []

    embedding = _embed_question(question)

    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    index = pc.Index(os.environ["PINECONE_INDEX_NAME"])

    # Group results by namespace to preserve per-book attribution
    results_by_namespace: dict[str, list[dict]] = {}
    with ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(_query_namespace, index, embedding, ns, top_k): ns
            for ns in namespaces
        }
        for future in as_completed(futures):
            ns = futures[future]
            try:
                passages = future.result()
                if passages:
                    # Sort within each book by score descending
                    results_by_namespace[ns] = sorted(passages, key=lambda p: p["score"], reverse=True)
            except Exception as e:
                import traceback
                print(f"ERROR: retrieval failed for namespace '{ns}': {e}")
                traceback.print_exc()

    # Flatten preserving per-book grouping (books ordered by their top passage score)
    books_by_top_score = sorted(
        results_by_namespace.values(),
        key=lambda passages: passages[0]["score"],
        reverse=True,
    )
    return [passage for book_passages in books_by_top_score for passage in book_passages]
