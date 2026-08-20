from typing import List, Dict, Any, Optional

from .embedding_service import embedding_service
from .chroma_service import chroma_service
from ..knowledge.knowledge_loader import knowledge_loader


class RAGService:
    """
    Retrieval-Augmented Generation service.

    Responsible for:

    1. Loading the travel knowledge base.
    2. Chunking documents.
    3. Creating embeddings.
    4. Storing embeddings in ChromaDB.
    5. Performing semantic search.
    6. Returning relevant context for the LLM.
    """

    def __init__(self):
        self.chunks: List[Dict[str, Any]] = []
        self._is_initialized = False

    def initialize(self):
        """
        Load the knowledge base and make sure its embeddings
        exist inside ChromaDB.
        """

        if self._is_initialized:
            return

        print("Initializing RAG Service...")

        # --------------------------------------------------
        # 1. Load and chunk knowledge
        # --------------------------------------------------

        self.chunks = knowledge_loader.load_and_chunk()

        if not self.chunks:
            print("No knowledge chunks found.")
            self._is_initialized = True
            return

        print(
            f"Loaded {len(self.chunks)} knowledge chunks."
        )

        # --------------------------------------------------
        # 2. Check whether Chroma already contains them
        # --------------------------------------------------

        existing_count = chroma_service.count()

        print(
            f"ChromaDB currently contains "
            f"{existing_count} documents."
        )

        # --------------------------------------------------
        # 3. Create embeddings and store them
        # --------------------------------------------------

        # We upsert every time.
        #
        # This makes changing faqs.json safe because
        # ChromaDB will update existing IDs.
        chunk_texts = [
            chunk["content"]
            for chunk in self.chunks
        ]

        print("Generating embeddings...")

        embeddings = embedding_service.encode(
            chunk_texts
        )

        print("Storing embeddings in ChromaDB...")

        chroma_service.add_documents(
            chunks=self.chunks,
            embeddings=embeddings
        )

        print(
            f"ChromaDB now contains "
            f"{chroma_service.count()} documents."
        )

        self._is_initialized = True

        print("RAG Service initialized successfully.")

    def search(
        self,
        query: str,
        destination: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search against ChromaDB.
        """

        if not self._is_initialized:
            self.initialize()

        if not self.chunks:
            return []

        # --------------------------------------------------
        # Create embedding for the user's question
        # --------------------------------------------------

        query_embedding = embedding_service.encode_single(
            query
        )

        # --------------------------------------------------
        # Search ChromaDB
        # --------------------------------------------------

        results = chroma_service.search(
            query_embedding=query_embedding,
            top_k=top_k,
            destination=destination
        )

        return results

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