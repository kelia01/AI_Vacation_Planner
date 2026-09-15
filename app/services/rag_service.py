from typing import List, Dict, Any, Optional

from .embedding_service import embedding_service
from .chroma_service import chroma_service


class RAGService:
    """
    Retrieval-Augmented Generation service.

    Responsible for querying the existing travel
    knowledge stored in ChromaDB.

    Knowledge ingestion and embedding generation are
    handled separately by the ingestion process.
    """

    def search(
        self,
        query: str,
        destination: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search against ChromaDB.
        """

        if chroma_service.count() == 0:
            return []

        query_embedding = (
            embedding_service.encode_single(query)
        )

        return chroma_service.search(
            query_embedding=query_embedding,
            top_k=top_k,
            destination=destination
        )

    def get_context(
        self,
        query: str,
        destination: Optional[str] = None,
        top_k: int = 3
    ) -> str:
        """
        Retrieve relevant knowledge and format it
        as context for the LLM.
        """

        results = self.search(
            query=query,
            destination=destination,
            top_k=top_k
        )

        if not results:
            return ""

        context_parts = []

        for i, result in enumerate(results):

            context_parts.append(
                f"[Source {i + 1}: "
                f"{result.get('title', 'Travel Information')}]\n"
                f"{result['content']}"
            )

        return "\n\n---\n\n".join(
            context_parts
        )

    def augment_prompt(
        self,
        user_query: str,
        destination: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve knowledge and build an augmented prompt.
        """

        results = self.search(
            query=user_query,
            destination=destination,
            top_k=3
        )

        context_parts = []

        for i, result in enumerate(results):

            context_parts.append(
                f"[Source {i + 1}: "
                f"{result.get('title', 'Travel Information')}]\n"
                f"{result['content']}"
            )

        context = "\n\n---\n\n".join(
            context_parts
        )

        if context:
            augmented_prompt = f"""
Context from the travel knowledge base:

{context}

Use the retrieved travel knowledge when relevant.

User question:

{user_query}
"""
        else:
            augmented_prompt = user_query

        return {
            "augmented_prompt": augmented_prompt,
            "retrieved_sources": results
        }


rag_service = RAGService()