from dotenv import load_dotenv
load_dotenv()
import os
from pinecone import Pinecone

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))

stats = index.describe_index_stats()
print("Namespaces in Pinecone:")
for ns, data in stats.namespaces.items():
    print("  '{}' — {} vectors".format(ns, data.vector_count))
