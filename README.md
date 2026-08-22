## RAG & Knowledge System

The Vacation Planner uses Retrieval-Augmented Generation (RAG) to provide the llm with relevant travel information from a custom knowledge base instead of relying only on the model's general knowledge.

### Architecture

```text
faqs.json
    ↓
KnowledgeLoader
    ↓
Document Chunking
    ↓
Sentence Transformers
    ↓
Embeddings
    ↓
ChromaDB
    ↓
Semantic Search
    ↓
RAG Service
    ↓
Relevant Context
    ↓
Claude
    ↓
AI Response
```

### Knowledge Base

Travel information is stored in:

app/knowledge/faqs.json

The knowledge base contains destination-specific information such as:

Travel tips
Budget advice
Attractions

KnowledgeLoader loads the documents and splits their content into smaller chunks before embedding.

### Embeddings

The system uses Sentence Transformers with the:

all-MiniLM-L6-v2

model.

Each knowledge-base chunk is converted into an embedding that represents its semantic meaning.

### Vector Database

ChromaDB is used as the vector database.

The generated embeddings, document content, and metadata are stored in a local ChromaDB collection.

When a user asks a question, the question is embedded and compared against the stored vectors to retrieve the most relevant travel information.

### Semantic Search

The RAG service performs semantic search using the user's question.

It can also filter results by destination.

For example:

Question:
"What is the best time to visit Paris?"

        ↓

ChromaDB Search

        ↓

Paris Travel Tips

The most relevant chunks are then provided to the LLM as context.

RAG Flow
User Question
      ↓
Create Query Embedding
      ↓
Search ChromaDB
      ↓
Retrieve Relevant Chunks
      ↓
Build Context
      ↓
Send Context + Question to Claude
      ↓
Generate Answer

The /ask endpoint returns the generated answer together with the retrieved sources.

Example:

{
  "answer": "...",
  "sources": [
    {
      "title": "Paris Travel Tips",
      "content": "..."
    }
  ],
  "rag_used": true
}

rag_used indicates whether relevant knowledge-base information was retrieved.

Project Structure
app/
├── knowledge/
│   ├── faqs.json
│   └── knowledge_loader.py
│
└── services/
    ├── embedding_service.py
    ├── rag_service.py
    └── rag_answer_service.py
API Documentation

The API is documented using FastAPI Swagger.

After starting the application:

http://localhost:8000/docs

The RAG functionality can be tested through:

POST /ask

The endpoint accepts a travel question and optionally a trip ID, which allows the system to use the trip's destination when retrieving relevant knowledge.
