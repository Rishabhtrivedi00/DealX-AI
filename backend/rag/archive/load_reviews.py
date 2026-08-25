import json
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"


def load_reviews():

    file_path = DATA_DIR / "reviews.json"

    with open(file_path, "r", encoding="utf-8") as file:
        reviews = json.load(file)

    documents = []

    for review in reviews:

        document = Document(
            page_content=review["review"],
            metadata={
                "product_id": review["product_id"],
                "rating": review["rating"]
            }
        )

        documents.append(document)

    return documents


if __name__ == "__main__":

    documents = load_reviews()

    print(f"Loaded documents: {len(documents)}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=200,
        chunk_overlap=30
    )

    chunks = splitter.split_documents(documents)

    print(f"Created chunks: {len(chunks)}")

    for chunk in chunks:

        print("\n--- CHUNK ---")
        print(chunk.page_content)
        print("Metadata:", chunk.metadata)