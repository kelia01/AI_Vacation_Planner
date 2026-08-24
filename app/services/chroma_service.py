import chromadb
from pathlib import Path
from typing import List, Dict, Any


class ChromaService:
    """
    Handles storage and semantic retrieval of travel knowledge
    using ChromaDB.
    """

    def __init__(self):
        
        self.persist_directory = (
            Path(__file__).resolve().parent.parent / "chroma_db"
        )

        self.persist_directory.mkdir(
            parents=True,
            exist_ok=True
        )

        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory)
        )

        self.collection = self.client.get_or_create_collection(
            name="travel_knowledge"
        )

    def add_documents(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ):
        """
        Add knowledge chunks and their embeddings to ChromaDB.
        """

        if not chunks:
            return

        ids = [chunk["id"] for chunk in chunks]

        documents = [
            chunk["content"]
            for chunk in chunks
        ]

        metadatas = [
            {
                "source_id": chunk.get("source_id", ""),
                "title": chunk.get("title", ""),
                "destination": chunk.get(
                    "destination",
                    "general"
                ),
                "category": chunk.get(
                    "category",
                    "general"
                ),
                "source": chunk.get(
                    "metadata",
                    {}
                ).get(
                    "source",
                    "faq"
                )
            }
            for chunk in chunks
        ]

        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        destination: str = None
    ) -> List[Dict[str, Any]]:
        """
        Search ChromaDB for the most relevant documents.
        """

        where = None

        if destination:
            where = {
                "$or": [
                    {
                        "destination": destination
                    },
                    {
                        "destination": "general"
                    }
                ]
            }

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where
        )

        if not results["documents"]:
            return []

        documents = results["documents"][0]
        ids = results["ids"][0]
        metadatas = results["metadatas"][0]

        distances = results.get(
            "distances",
            [[]]
        )[0]

        retrieved = []

        for i, document in enumerate(documents):

            distance = (
                distances[i]
                if i < len(distances)
                else None
            )

            # Convert distance to a simple similarity score.
            similarity = (
                1 - distance
                if distance is not None
                else None
            )

            retrieved.append(
                {
                    "id": ids[i],
                    "content": document,
                    "similarity_score": similarity,
                    **metadatas[i]
                }
            )

        return retrieved

    def count(self) -> int:
        """Return the number of documents stored."""

        return self.collection.count()

    def clear(self):
        """Delete the current collection."""

        self.client.delete_collection(
            name="travel_knowledge"
        )

        self.collection = self.client.get_or_create_collection(
            name="travel_knowledge"
        )


chroma_service = ChromaService()