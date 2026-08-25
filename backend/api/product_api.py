import requests


UPCITEMDB_URL = "https://api.upcitemdb.com/prod/trial/lookup"


def get_product_from_api(barcode: str):

    response = requests.get(
        UPCITEMDB_URL,
        params={"upc": barcode},
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    if data.get("total", 0) == 0:
        return None

    item = data["items"][0]

    # Stable ID for external products
    product_id = f"EXT-{barcode}"

    return {
    "product_id": product_id,
    "barcode": item.get("ean") or item.get("upc"),
    "asin": item.get("asin"),
    "name": item.get("title"),
    "brand": item.get("brand"),
    "model": item.get("model"),
    "category": item.get("category"),
    "description": item.get("description"),
    "images": item.get("images", []),
    "price": item.get("lowest_recorded_price"),
    "currency": item.get("currency")
    }