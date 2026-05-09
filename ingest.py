import argparse
import os
import time

from dotenv import load_dotenv
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec

from config import BOOKS

load_dotenv()

PINECONE_INDEX_NAME = os.environ["PINECONE_INDEX_NAME"]
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536
CHUNK_SIZE = 400
CHUNK_OVERLAP = 50
UPSERT_BATCH_SIZE = 100


def get_book(namespace: str) -> dict:
    for book in BOOKS:
        if book["namespace"] == namespace:
            return book
    return None


def extract_text(pdf_path: str) -> tuple[str, int]:
    reader = PdfReader(pdf_path)
    pages = len(reader.pages)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return text, pages


def chunk_text(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name="cl100k_base",
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    return splitter.split_text(text)


def embed_chunks(chunks: list[str], client: OpenAI) -> list[list[float]]:
    print(f"Embedding {len(chunks)} chunks...")
    embeddings = []
    # OpenAI allows up to 2048 inputs per call; batch in 500s to stay safe
    batch_size = 500
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        embeddings.extend([item.embedding for item in response.data])
        print(f"  Embedded {min(i + batch_size, len(chunks))}/{len(chunks)}")
    return embeddings


def get_or_create_index(pc: Pinecone) -> object:
    existing = [idx.name for idx in pc.list_indexes()]
    if PINECONE_INDEX_NAME not in existing:
        print(f"Creating Pinecone index '{PINECONE_INDEX_NAME}'...")
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=EMBEDDING_DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        # Wait for index to be ready
        while not pc.describe_index(PINECONE_INDEX_NAME).status["ready"]:
            time.sleep(1)
        print("Index created.")
    return pc.Index(PINECONE_INDEX_NAME)


def upsert_vectors(index, namespace: str, book: dict, chunks: list[str], embeddings: list[list[float]]) -> None:
    vectors = [
        {
            "id": f"{namespace}-{i}",
            "values": embeddings[i],
            "metadata": {
                "namespace": namespace,
                "title": book["title"],
                "author": book["author"],
                "chunk_index": i,
                "text": chunks[i],
            },
        }
        for i in range(len(chunks))
    ]

    print(f"Upserting {len(vectors)} vectors to namespace '{namespace}'...")
    for i in range(0, len(vectors), UPSERT_BATCH_SIZE):
        batch = vectors[i : i + UPSERT_BATCH_SIZE]
        attempts = 0
        while attempts < 2:
            try:
                index.upsert(vectors=batch, namespace=namespace)
                break
            except Exception as e:
                attempts += 1
                if attempts == 2:
                    raise
                print(f"  Upsert failed ({e}), retrying...")
        print(f"  Upserted {min(i + UPSERT_BATCH_SIZE, len(vectors))}/{len(vectors)}")


def main():
    parser = argparse.ArgumentParser(description="Ingest a book PDF into Pinecone.")
    parser.add_argument("--namespace", required=True, help="Book namespace (must exist in config.py)")
    args = parser.parse_args()
    namespace = args.namespace

    book = get_book(namespace)
    if not book:
        print(f"Error: namespace '{namespace}' not found in config.py")
        print("Available namespaces:", [b["namespace"] for b in BOOKS])
        raise SystemExit(1)

    pdf_path = f"books/{namespace}.pdf"
    if not os.path.exists(pdf_path):
        print(f"Error: PDF not found at '{pdf_path}'")
        raise SystemExit(1)

    print(f"Found: {book['title']} by {book['author']}")
    print(f"Loading PDF: {pdf_path}")

    text, num_pages = extract_text(pdf_path)
    print(f"Extracted {num_pages} pages")

    chunks = chunk_text(text)
    print(f"Split into {len(chunks)} chunks")

    openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    embeddings = embed_chunks(chunks, openai_client)

    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    index = get_or_create_index(pc)

    upsert_vectors(index, namespace, book, chunks, embeddings)

    print(f"Done. {namespace} is ready to query.")


if __name__ == "__main__":
    main()
