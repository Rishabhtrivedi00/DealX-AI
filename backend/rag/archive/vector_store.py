from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from backend.rag.archive.load_reviews import load_reviews
from langchain_text_splitters import RecursiveCharacterTextSplitter


# -----------------------------
# 1. Load reviews
# -----------------------------

documents = load_reviews()

print(f"Loaded documents: {len(documents)}")


# -----------------------------
# 2. Split documents
# -----------------------------

splitter = RecursiveCharacterTextSplitter(
    chunk_size=200,
    chunk_overlap=30
)

chunks = splitter.split_documents(documents)

print(f"Created chunks: {len(chunks)}")


# -----------------------------
# 3. Create embedding model
# -----------------------------

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


# -----------------------------
# 4. Create ChromaDB
# -----------------------------

vector_store = Chroma(
    collection_name="dealx_reviews",
    embedding_function=embeddings,
    persist_directory="../../chroma_db"
)


# -----------------------------
# 5. Add documents
# -----------------------------

vector_store.add_documents(chunks)

print("Reviews successfully stored in ChromaDB!")