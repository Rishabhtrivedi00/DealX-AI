from langchain_huggingface import HuggingFaceEmbeddings


def create_embedding_model():

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    return embeddings


if __name__ == "__main__":

    embeddings = create_embedding_model()

    text = "The battery life is excellent."

    vector = embeddings.embed_query(text)

    print("Text:")
    print(text)

    print("\nVector:")
    print(vector)

    print("\nVector dimensions:")
    print(len(vector))
    