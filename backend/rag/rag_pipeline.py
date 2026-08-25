import os
import json
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings


# ============================================================
# 1. PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent

CHROMA_DIR = BASE_DIR / "chroma_db"

REVIEWS_FILE = BASE_DIR / "backend" / "data" / "reviews.json"


# ============================================================
# 2. LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv(
    BASE_DIR / "backend" / ".env"
)


# ============================================================
# 3. GROQ CLIENT
# ============================================================

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


# ============================================================
# 4. HUGGING FACE EMBEDDINGS
# ============================================================

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


# ============================================================
# 5. CHROMADB
# ============================================================

vector_store = Chroma(
    collection_name="dealx_reviews",
    embedding_function=embeddings,
    persist_directory=str(CHROMA_DIR)
)


def load_local_reviews(product_id):

    with open(REVIEWS_FILE, "r", encoding="utf-8") as file:
        reviews = json.load(file)

    return [
        review
        for review in reviews
        if review.get("product_id") == product_id
    ]


def answer_from_reviews(reviews, query):

    context = "\n\n".join(
        [
            f"Review: {review['review']}\n"
            f"Rating: {review.get('rating')}"
            for review in reviews
        ]
    )

    prompt = f"""
You are DealX-AI, an AI shopping assistant.

Answer the user's question using ONLY the review information below.
Do not invent information. If the reviews do not contain enough information,
clearly say that it is not available.

When appropriate, structure the answer using:

Pros:
List positive points mentioned by reviewers.

Cons:
List negative or weak points mentioned by reviewers.

Verdict:
Give a short buying-oriented conclusion.

REVIEWS:
{context}

USER QUESTION:
{query}
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    return clean_text_encoding(response.choices[0].message.content)


# ============================================================
# 6. ASK PRODUCT USING RAG
# ============================================================

def ask_product(product_id, query):

    local_reviews = load_local_reviews(product_id)

    if local_reviews:
        return answer_from_reviews(local_reviews, query)

    # --------------------------------------------------------
    # Retrieve relevant reviews
    # --------------------------------------------------------

    results = vector_store.similarity_search(
        query,
        k=4,
        filter={
            "product_id": product_id
        }
    )

    # --------------------------------------------------------
    # No reviews found
    # --------------------------------------------------------

    if not results:

        return (
            "I don't have enough review information "
            "about this product to answer that question."
        )

    # --------------------------------------------------------
    # Prepare context
    # --------------------------------------------------------

    context = "\n\n".join(
        [
            f"Review: {doc.page_content}\n"
            f"Product ID: {doc.metadata.get('product_id')}\n"
            f"Rating: {doc.metadata.get('rating')}"
            for doc in results
        ]
    )

    # --------------------------------------------------------
    # Prompt
    # --------------------------------------------------------

    prompt = f"""
You are DealX-AI, an AI shopping assistant.

Answer the user's question using ONLY the review
information provided below.

Do not invent information.

If the reviews do not contain enough information,
clearly say that the information is not available.

When appropriate, structure the answer using:

Pros:
List positive points mentioned by reviewers.

Cons:
List negative or weak points mentioned by reviewers.

Verdict:
Give a short buying-oriented conclusion.

Important:

- Only include information supported by the reviews.
- Do not invent pros or cons.
- Do not use outside knowledge.
- Keep the answer concise and easy to understand.

REVIEWS:

{context}

USER QUESTION:

{query}
"""

    # --------------------------------------------------------
    # Send to Groq
    # --------------------------------------------------------

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    return clean_text_encoding(
        response.choices[0].message.content
    )


def ask_external_product(barcode, query, reviews):

    return answer_from_reviews(reviews, query)


# ============================================================
# 7. GENERATE EXTERNAL PRODUCT SUMMARY
# ============================================================

def generate_product_summary(product):

    """
    Generate an AI shopping assessment from external
    product information.

    This is NOT a customer-review summary.
    """

    # --------------------------------------------------------
    # Prepare product information
    # --------------------------------------------------------

    context = f"""
Product Name:
{product.get("name") or "Not available"}

Brand:
{product.get("brand") or "Not available"}

Model:
{product.get("model") or "Not available"}

Category:
{product.get("category") or "Not available"}

Price:
{product.get("price") or "Not available"}

Currency:
{product.get("currency") or "Not available"}

Description:
{product.get("description") or "Not available"}
"""

    # --------------------------------------------------------
    # Prompt
    # --------------------------------------------------------

    prompt = f"""
You are DealX-AI, an AI shopping assistant.

Analyze the product information below and provide
a useful shopping assessment.

IMPORTANT:

This is product information, NOT verified customer reviews.

Do not claim that customers liked or disliked anything.

Do not invent specifications.

You may make reasonable AI-based assessments from the
available product information.

If something cannot be determined, do not present it
as a confirmed fact.

Return ONLY this structure:

OVERALL:
Write one short paragraph describing the product.

PROS:
- advantage 1
- advantage 2
- advantage 3

CONS:
- possible limitation 1
- possible limitation 2

VERDICT:
Write one short buying-oriented conclusion.

Rules:

- Keep the answer concise.
- Do not invent product specifications.
- Do not pretend these are customer reviews.
- Pros must be based on available product information.
- Cons must be reasonable limitations based on the information.
- If a con cannot reasonably be determined, do not invent one.
- The verdict should help a shopper make a decision.

PRODUCT INFORMATION:

{context}
"""

    # --------------------------------------------------------
    # Send to Groq
    # --------------------------------------------------------

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    answer = response.choices[0].message.content

    # --------------------------------------------------------
    # Debug output
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("GROQ EXTERNAL PRODUCT SUMMARY")
    print("=" * 60)
    print(answer)
    print("=" * 60)
    print()

    # --------------------------------------------------------
    # Parse response
    # --------------------------------------------------------

    return parse_summary(answer)


# ============================================================
# 8. PARSE SUMMARY
# ============================================================

def parse_summary(answer):

    overall = ""
    pros = []
    cons = []
    verdict = ""

    current_section = None

    # --------------------------------------------------------
    # Process every line
    # --------------------------------------------------------

    for raw_line in answer.splitlines():

        line = raw_line.strip()

        if not line:
            continue

        # Remove markdown formatting
        clean_line = (
            line
            .replace("**", "")
            .replace("__", "")
            .strip()
        )

        upper = clean_line.upper()

        # ====================================================
        # OVERALL
        # ====================================================

        if upper.startswith("OVERALL"):

            current_section = "overall"

            if ":" in clean_line:

                overall = clean_line.split(
                    ":",
                    1
                )[1].strip()

            continue

        # ====================================================
        # PROS
        # ====================================================

        if upper.startswith("PROS"):

            current_section = "pros"

            if ":" in clean_line:

                remaining = clean_line.split(
                    ":",
                    1
                )[1].strip()

                if remaining:

                    pros.append(
                        clean_bullet(remaining)
                    )

            continue

        # ====================================================
        # CONS
        # ====================================================

        if upper.startswith("CONS"):

            current_section = "cons"

            if ":" in clean_line:

                remaining = clean_line.split(
                    ":",
                    1
                )[1].strip()

                if remaining:

                    cons.append(
                        clean_bullet(remaining)
                    )

            continue

        # ====================================================
        # VERDICT
        # ====================================================

        if upper.startswith("VERDICT"):

            current_section = "verdict"

            if ":" in clean_line:

                verdict = clean_line.split(
                    ":",
                    1
                )[1].strip()

            continue

        # ====================================================
        # SECTION CONTENT
        # ====================================================

        if current_section == "overall":

            if overall:

                overall += " " + clean_line

            else:

                overall = clean_line

        elif current_section == "pros":

            if is_bullet(clean_line):

                pros.append(
                    clean_bullet(clean_line)
                )

        elif current_section == "cons":

            if is_bullet(clean_line):

                cons.append(
                    clean_bullet(clean_line)
                )

        elif current_section == "verdict":

            if verdict:

                verdict += " " + clean_line

            else:

                verdict = clean_line

    # --------------------------------------------------------
    # Clean encoding
    # --------------------------------------------------------

    overall = clean_text_encoding(
        overall.strip()
    )

    pros = [
        clean_text_encoding(pro)
        for pro in pros
    ]

    cons = [
        clean_text_encoding(con)
        for con in cons
    ]

    verdict = clean_text_encoding(
        verdict.strip()
    )

    # --------------------------------------------------------
    # Return final structure
    # --------------------------------------------------------

    return {
        "overall": overall,
        "pros": pros,
        "cons": cons,
        "verdict": verdict
    }


# ============================================================
# 9. CHECK BULLET
# ============================================================

def is_bullet(text):

    return (
        text.startswith("-")
        or text.startswith("•")
        or text.startswith("*")
    )


# ============================================================
# 10. CLEAN BULLET
# ============================================================

def clean_bullet(text):

    return (
        text
        .lstrip("-")
        .lstrip("•")
        .lstrip("*")
        .strip()
    )


# ============================================================
# 11. CLEAN TEXT ENCODING
# ============================================================

def clean_text_encoding(text):

    if not isinstance(text, str):
        return text

    # Common UTF-8 -> Windows-1252 corruption
    replacements = {
        "â¯": " ",
        "â€“": "-",
        "â€”": "-",
        "â€™": "'",
        "â€œ": '"',
        "â€": '"',
        "â€¦": "...",
        "â€": '"',
        "Â": "",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


# ============================================================
# 12. TEST
# ============================================================

if __name__ == "__main__":

    test_product = {

        "product_id": "EXT-TEST",

        "name": (
            "Apple iPhone 6, Space Gray, 64 GB"
        ),

        "brand": "Apple",

        "model": "MG5A2LL/A",

        "category": "Mobile Phones",

        "price": 3.79,

        "currency": "",

        "description": (
            "Retina HD display, "
            "12MP camera, "
            "Touch ID, "
            "64GB storage."
        )
    }

    result = generate_product_summary(
        test_product
    )

    print()
    print("=" * 60)
    print("FINAL PARSED RESULT")
    print("=" * 60)

    print(result)

    print("=" * 60)