import json
from pathlib import Path

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings


# --------------------------------
# Project paths
# --------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent.parent

CHROMA_DIR = BASE_DIR / "chroma_db"

REVIEWS_FILE = (
    BASE_DIR
    / "backend"
    / "data"
    / "reviews"
    / "external_reviews.json"
)


# --------------------------------
# Embedding model
# --------------------------------

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


# --------------------------------
# ChromaDB
# --------------------------------

vector_store = Chroma(
    collection_name="dealx_external_reviews",
    embedding_function=embeddings,
    persist_directory=str(CHROMA_DIR)
)


# --------------------------------
# Load reviews
# --------------------------------

def load_reviews():

    with open(
        REVIEWS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# --------------------------------
# Add reviews to ChromaDB
# --------------------------------

def add_external_reviews():

    reviews = load_reviews()

    documents = []

    for review in reviews:

        documents.append(
            {
                "page_content": review["review"],

                "metadata": {
                    "barcode": review["barcode"],
                    "rating": review["rating"],
                    "source": "external"
                }
            }
        )

    texts = [
        item["page_content"]
        for item in documents
    ]

    metadatas = [
        item["metadata"]
        for item in documents
    ]

    vector_store.add_texts(
        texts=texts,
        metadatas=metadatas
    )

    print(
        f"Added {len(texts)} external reviews to ChromaDB."
    )


# --------------------------------
# Test
# --------------------------------

if __name__ == "__main__":

    add_external_reviews()