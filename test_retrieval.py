from router import get_relevant_books
from retriever import retrieve_passages
from orchestrator import synthesize

QUESTION = "What makes a good strategy, and how do I know if mine is bad?"

print(f"Question: {QUESTION}\n")

print("=" * 60)
print("ROUTER")
print("=" * 60)
namespaces = get_relevant_books(QUESTION, [])
print(f"Relevant namespaces: {namespaces}\n")

print("=" * 60)
print("RETRIEVER")
print("=" * 60)
passages = retrieve_passages(QUESTION, namespaces)
print(f"Retrieved {len(passages)} passages (score >= 0.70)\n")

current_book = None
for p in passages:
    if p["title"] != current_book:
        current_book = p["title"]
        print(f"\n--- {p['title']} by {p['author']} ---")
    print(f"\n  [{p['score']:.3f}] {p['text'][:300].strip()}...")

print("\n")
print("=" * 60)
print("ORCHESTRATOR")
print("=" * 60)
answer = synthesize(QUESTION, passages, [])
print(answer)
