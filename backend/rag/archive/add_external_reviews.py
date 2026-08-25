from langchain_core.documents import Document
from backend.rag.rag_pipeline import vector_store


PRODUCT_ID = "EXT-0885909950805"
BARCODE = "0885909950805"


reviews = [
    {
        "rating": 4,
        "text": "The phone has a good design and feels compact and easy to use. The camera takes decent photos, and the phone is simple to operate for everyday tasks."
    },
    {
        "rating": 3,
        "text": "The battery life is weak compared with newer phones. It needs charging fairly often, especially with regular daily use."
    },
    {
        "rating": 3,
        "text": "Performance is acceptable for basic tasks, but multitasking can feel slow. Some newer apps may feel sluggish on the device."
    },
    {
        "rating": 4,
        "text": "The design and build quality are good, and the phone is compact. It works well for basic everyday use, although battery life could be better."
    }
]


documents = []

for review in reviews:

    documents.append(
        Document(
            page_content=review["text"],
            metadata={
                "product_id": PRODUCT_ID,
                "barcode": BARCODE,
                "rating": review["rating"]
            }
        )
    )


vector_store.add_documents(documents)

print(f"Added {len(documents)} external reviews to ChromaDB.")
print(f"Product ID: {PRODUCT_ID}")
