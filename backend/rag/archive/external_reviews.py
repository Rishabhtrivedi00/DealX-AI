import os
import requests

from dotenv import load_dotenv
from langchain_core.documents import Document

from backend.rag.rag_pipeline import vector_store


# --------------------------------
# Load environment variables
# --------------------------------

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../..")
)

load_dotenv(
    os.path.join(BASE_DIR, "backend", ".env")
)


AMAZONCRAWLER_API_KEY = os.getenv(
    "AMAZONCRAWLER_API_KEY"
)

REVIEWS_URL = (
    "https://amazoncrawler.com/v1/products/reviews"
)


# --------------------------------
# Fetch external reviews
# --------------------------------

def fetch_amazon_reviews(
    asin,
    product_id,
    marketplace="US",
    zip_code="10001"
):

    if not AMAZONCRAWLER_API_KEY:
        raise ValueError(
            "AMAZONCRAWLER_API_KEY is missing from backend/.env"
        )

    response = requests.get(
        REVIEWS_URL,
        params={
            "asin": asin,
            "marketplace": marketplace,
            "zip": zip_code,
            "page": 1
        },
        headers={
            "x-api-key": AMAZONCRAWLER_API_KEY
        },
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    reviews = data.get("reviews", [])

    print(
        f"Fetched {len(reviews)} reviews for ASIN {asin}"
    )

    return reviews


# --------------------------------
# Add reviews to ChromaDB
# --------------------------------

def add_external_reviews(
    asin,
    product_id
):

    reviews = fetch_amazon_reviews(
        asin=asin,
        product_id=product_id
    )

    if not reviews:
        print("No external reviews found.")
        return 0

    documents = []

    for review in reviews:

        body = review.get("body", "").strip()

        if not body:
            continue

        title = review.get("title", "")

        rating = review.get("rating")

        verified = review.get(
            "verified_purchase",
            False
        )

        helpful_votes = review.get(
            "helpful_votes",
            0
        )

        review_text = f"""
Review Title: {title}

Review:
{body}

Rating: {rating}

Verified Purchase: {verified}

Helpful Votes: {helpful_votes}
""".strip()

        metadata = {
            "product_id": product_id,
            "source": "amazon_external",
            "asin": asin,
            "rating": rating,
            "verified_purchase": verified
        }

        documents.append(
            Document(
                page_content=review_text,
                metadata=metadata
            )
        )

    if not documents:
        print("No usable review text found.")
        return 0

    # Add documents to existing ChromaDB
    vector_store.add_documents(documents)

    print(
        f"Added {len(documents)} external reviews to ChromaDB."
    )

    return len(documents)


# --------------------------------
# Test
# --------------------------------

if __name__ == "__main__":

    asin = "B00NQGOZV0"
    product_id = "EXT-0885909950805"

    count = add_external_reviews(
        asin=asin,
        product_id=product_id
    )

    print(
        f"\nSuccessfully added {count} reviews."
    )