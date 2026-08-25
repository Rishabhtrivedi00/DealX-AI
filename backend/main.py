from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from backend.rag.rag_pipeline import (
    ask_product,
    ask_external_product,
    generate_product_summary
)

from backend.api.product_api import get_product_from_api

import json
from pathlib import Path


# ============================================================
# 1. FASTAPI APP
# ============================================================

app = FastAPI(
    title="DealX-AI"
)


# ============================================================
# 2. CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|[\w.-]+):5173",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# 3. REQUEST MODELS
# ============================================================

class AskRequest(BaseModel):

    product_id: str
    question: str


class BarcodeAskRequest(BaseModel):

    barcode: str
    question: str


# ============================================================
# 4. PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

PRODUCTS_FILE = (
    BASE_DIR
    / "data"
    / "products.json"
)

EXTERNAL_REVIEWS_FILE = (
    BASE_DIR
    / "data"
    / "reviews"
    / "external_reviews.json"
)


# ============================================================
# 5. LOAD LOCAL PRODUCTS
# ============================================================

def load_products():

    with open(
        PRODUCTS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def load_external_reviews():

    with open(
        EXTERNAL_REVIEWS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ============================================================
# 6. HOME
# ============================================================

@app.get("/")
def home():

    return {
        "message": "DealX-AI backend is running!"
    }


# ============================================================
# 7. GET ALL LOCAL PRODUCTS
# ============================================================

@app.get("/products")
def get_products():

    products = load_products()

    return {
        "count": len(products),
        "products": products
    }


# ============================================================
# 8. FIND PRODUCT BY BARCODE
# ============================================================

@app.get("/product/barcode/{barcode}")
def get_product_by_barcode(
    barcode: str
):

    products = load_products()

    for product in products:

        if product["barcode"] == barcode:

            return {
                "found": True,
                "source": "local_database",
                "product": product
            }

    # --------------------------------------------------------
    # Try external product API only after local lookup
    # --------------------------------------------------------

    try:

        api_product = get_product_from_api(
            barcode
        )

        if api_product:

            # Create an external product ID
            api_product["product_id"] = (
                f"EXT-{barcode}"
            )

            return {
                "found": True,
                "source": "external_api",
                "product": api_product
            }

    except Exception as error:

        print(
            f"External API error: {error}"
        )

    # Product not found
    # --------------------------------------------------------

    raise HTTPException(
        status_code=404,
        detail="Product not found"
    )


# ============================================================
# 9. ASK DEALX-AI USING PRODUCT ID
# ============================================================

@app.post("/ask")
def ask_question(
    request: AskRequest
):

    # --------------------------------------------------------
    # Only products with RAG data can currently use
    # this endpoint.
    # --------------------------------------------------------

    answer = ask_product(
        request.product_id,
        request.question
    )

    return {
        "product_id": request.product_id,
        "question": request.question,
        "answer": answer
    }


# ============================================================
# 10. ASK DEALX-AI USING BARCODE
# ============================================================

@app.post("/ask/barcode")
def ask_by_barcode(
    request: BarcodeAskRequest
):

    # --------------------------------------------------------
    # First check local products
    # --------------------------------------------------------

    products = load_products()

    product = None

    for item in products:

        if item["barcode"] == request.barcode:

            product = item

            break

    # --------------------------------------------------------
    # LOCAL PRODUCT
    # --------------------------------------------------------

    if product:

        product_id = product["product_id"]

        answer = ask_product(
            product_id,
            request.question
        )

        return {
            "barcode": request.barcode,
            "product_id": product_id,
            "product_name": product.get("name"),
            "question": request.question,
            "answer": answer
        }

    external_reviews = [
        review
        for review in load_external_reviews()
        if review["barcode"] == request.barcode
    ]

    if external_reviews:

        answer = ask_external_product(
            request.barcode,
            request.question,
            external_reviews
        )

        return {
            "barcode": request.barcode,
            "product_id": f"EXT-{request.barcode}",
            "question": request.question,
            "answer": answer
        }

    # External product information fallback

    try:

        external_product = get_product_from_api(
            request.barcode
        )

        if external_product:

            external_product["product_id"] = (
                f"EXT-{request.barcode}"
            )

            # For external products, use the
            # product information directly.

            product_context = f"""
Product Name:
{external_product.get("name")}

Brand:
{external_product.get("brand")}

Model:
{external_product.get("model")}

Category:
{external_product.get("category")}

Price:
{external_product.get("price")}

Description:
{external_product.get("description")}
"""

            from backend.rag.rag_pipeline import client

            prompt = f"""
You are DealX-AI, an AI shopping assistant.

Answer the user's question using the available
product information below.

Do not invent specifications.

If the information is not available, clearly say
that it is not available.

The answer does not need to be perfectly accurate
because this is an AI product-assessment prototype,
but do not intentionally make up facts.

PRODUCT INFORMATION:

{product_context}

USER QUESTION:

{request.question}
"""

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

            answer = (
                response
                .choices[0]
                .message
                .content
            )

            return {
                "barcode": request.barcode,
                "product_id": external_product[
                    "product_id"
                ],
                "product_name": external_product.get(
                    "name"
                ),
                "question": request.question,
                "answer": answer
            }

    except Exception as error:

        print(
            f"External product question error: {error}"
        )

    # --------------------------------------------------------
    # Product not found
    # --------------------------------------------------------

    raise HTTPException(
        status_code=404,
        detail="Product not found for this barcode"
    )


# ============================================================
# 11. PRODUCT AI SUMMARY
# ============================================================

@app.get("/product/{product_id}/summary")
def get_product_summary(
    product_id: str
):

    # --------------------------------------------------------
    # 1. Check local products
    # --------------------------------------------------------

    products = load_products()

    for product in products:

        if product["product_id"] == product_id:

            summary = generate_product_summary(
                product
            )

            return {
                "product_id": product_id,
                "summary": summary
            }

    # --------------------------------------------------------
    # 2. External product
    # --------------------------------------------------------

    if product_id.startswith("EXT-"):

        barcode = product_id.replace(
            "EXT-",
            "",
            1
        )

        try:

            external_product = (
                get_product_from_api(
                    barcode
                )
            )

            if external_product:

                external_product["product_id"] = (
                    product_id
                )

                summary = (
                    generate_product_summary(
                        external_product
                    )
                )

                return {
                    "product_id": product_id,
                    "summary": summary
                }

        except Exception as error:

            print(
                f"External summary error: {error}"
            )

    # --------------------------------------------------------
    # 3. Product unavailable
    # --------------------------------------------------------

    raise HTTPException(
        status_code=404,
        detail="Product not found"
    )