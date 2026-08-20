import os

from anthropic import Anthropic

from app.services.rag_service import rag_service


api_key = os.getenv("ANTHROPIC_API_KEY")

MODEL = "claude-haiku-4-5"

client = Anthropic(api_key=api_key)


def answer_travel_question(
    question: str,
    destination: str = None
):
    """
    Answer a travel question using RAG.

    Flow:
    1. Load the knowledge base.
    2. Generate embeddings.
    3. Perform semantic search.
    4. Retrieve relevant travel knowledge.
    5. Add the retrieved knowledge to Claude's prompt.
    6. Return the answer together with the retrieved sources.
    """

    print("\n========== RAG DEBUG ==========")
    print("Question:", question)
    print("Destination:", destination)

    # ---------------------------------------------------------
    # 1. RETRIEVE KNOWLEDGE
    # ---------------------------------------------------------

    try:
        rag_service.initialize()

        print("Chunks loaded:", len(rag_service.chunks))
        print(
            "Embeddings loaded:",
            len(rag_service.chunk_embeddings)
        )

        sources = rag_service.search(
            query=question,
            destination=destination,
            top_k=3
        )

        print("Retrieved sources:", len(sources))

        for source in sources:
            print(
                f"- {source.get('title')} "
                f"(score: {source.get('similarity_score')})"
            )

        context = rag_service.get_context(
            query=question,
            destination=destination,
            top_k=3
        )

        print("Context:")
        print(context)
        print("===============================\n")

    except Exception as e:
        print("\n========== RAG ERROR ==========")
        print(type(e).__name__, ":", str(e))
        print("===============================\n")

        # Do NOT silently pretend RAG worked.
        # For development, expose the error.
        raise

    # ---------------------------------------------------------
    # 2. BUILD PROMPT
    # ---------------------------------------------------------

    if context:

        prompt = f"""
You are a helpful travel assistant.

You have access to the following information retrieved
from the Vacation Planner's travel knowledge base.

===== RELEVANT TRAVEL KNOWLEDGE =====

{context}

===== END TRAVEL KNOWLEDGE =====

Answer the user's question using the retrieved knowledge
when it is relevant.

If the retrieved knowledge does not contain enough
information to answer the question, you may use your
general knowledge, but do not claim that information came
from the knowledge base unless it actually did.

User question:

{question}

Answer clearly and concisely.
"""

    else:

        prompt = f"""
You are a helpful travel assistant.

No relevant information was found in the travel knowledge
base.

Answer the following question using your general knowledge.

User question:

{question}

Answer clearly and concisely.
"""

    # ---------------------------------------------------------
    # 3. SEND AUGMENTED PROMPT TO CLAUDE
    # ---------------------------------------------------------

    try:

        response = client.messages.create(
            model=MODEL,
            max_tokens=500,
            system=(
                "You are an expert travel assistant. "
                "Give accurate and useful travel information."
            ),
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        text = "".join(
            block.text
            for block in response.content
            if block.type == "text"
        )

    except Exception as e:

        print("Claude error:", str(e))

        raise


    # ---------------------------------------------------------
    # 4. RETURN ANSWER + SOURCES
    # ---------------------------------------------------------

    return {
        "answer": text.strip(),

        "sources": [
            {
                "title": source.get(
                    "title",
                    "Travel Information"
                ),
                "content": source.get(
                    "content",
                    ""
                ),
                "similarity_score": source.get(
                    "similarity_score"
                )
            }
            for source in sources
        ],

        "rag_used": bool(sources)
    }