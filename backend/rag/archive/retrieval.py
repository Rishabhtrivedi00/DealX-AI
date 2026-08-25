from pathlib import Path

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings


# --------------------------------
# 1. Project paths
# --------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CHROMA_DIR = BASE_DIR / "chroma_db"


# --------------------------------
# 2. Load the embedding model
# --------------------------------

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


# --------------------------------
# 3. Connect to existing ChromaDB
# --------------------------------

vector_store = Chroma(
    collection_name="dealx_reviews",
    embedding_function=embeddings,
    persist_directory=str(CHROMA_DIR)
)


# --------------------------------
# 4. Search reviews
# --------------------------------

# --------------------------------
# 4. Search reviews for a product
# --------------------------------

product_id = "P001"

query = "What are the battery related comments?"

results = vector_store.similarity_search(
    query,
    k=2,
    filter={"product_id": product_id}
)


# --------------------------------
# 5. Display results
# --------------------------------

print("\nUser Query:")
print(query)

print("\nRelevant Reviews:")

for i, document in enumerate(results, start=1):

    print(f"\n--- Result {i} ---")
    print("Review:", document.page_content)
    print("Metadata:", document.metadata)