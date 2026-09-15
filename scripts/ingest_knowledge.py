from app.knowledge.knowledge_loader import knowledge_loader
from app.services.embedding_service import embedding_service
from app.services.chroma_service import chroma_service


def ingest_knowledge():
    chunks = knowledge_loader.load_and_chunk()

    if not chunks:
        print("No knowledge chunks found.")
        return

    texts = [chunk["content"] for chunk in chunks]

    embeddings = embedding_service.encode(texts)

    chroma_service.add_documents(
        chunks=chunks,
        embeddings=embeddings
    )

    print(f"Indexed {len(chunks)} chunks.")
    print(f"ChromaDB contains {chroma_service.count()} documents.")


if __name__ == "__main__":
    ingest_knowledge()