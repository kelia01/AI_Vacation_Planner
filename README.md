# AI Vacation Planner

An intelligent trip planning API that evolved across 6 phases — from a basic REST API to a full multimodal AI agent with voice input, image understanding, MCP-connected tools, and text-to-speech output.

Built with **FastAPI**, **LangGraph**, and **MCP**.

---

## Quick Start

```bash
git clone <repo-url>
cd AI_Vacation_Planner
uv sync
cp .env.example .env   # fill in your keys
uv run uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

---

## Environment Variables

```env
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional — Text-to-speech
ELEVENLABS_API_KEY=...
```

> Speech-to-text uses the free Google Web Speech API via `SpeechRecognition` .

---

## Project Structure

```
app/
├── main.py                        # FastAPI app, CORS, router registration
├── database.py                    # SQLAlchemy engine + session
├── models.py                      # ORM models: User, Trip, Itinerary, ItineraryDay
├── schemas.py                     # Shared Pydantic request/response schemas
├── crud.py                        # Raw DB operations
├── auth.py                        # Password hashing, JWT
├── dependencies.py                # get_current_user dependency
│
├── routers/
│   ├── auth.py                    # POST /auth/register, /auth/login
│   ├── users.py                   # GET /users/me
│   ├── trips.py                   # CRUD /trips
│   ├── itineraries.py             # GET /itineraries/{trip_id}
│   └── agent.py                   # POST /agent/plan, /agent/review
│
├── services/
│   ├── trip_service.py            # Trip business logic
│   ├── itinerary_service.py       # Itinerary business logic
│   ├── multimodal_service.py      # STT, image analysis, TTS
│   ├── auth_service.py            # Register/login logic
│   ├── weather_service.py         # Open-Meteo weather API
│   ├── rag_service.py             # ChromaDB semantic search
│   ├── embedding_service.py       # Sentence-transformer embeddings
│   └── chroma_service.py          # ChromaDB client wrapper
│
├── agent/
│   ├── graph.py                   # LangGraph workflow
│   ├── state.py                   # AgentState TypedDict
│   ├── tools.py                   # AGENT_TOOLS: weather + RAG
│   ├── mcp_tools.py               # MCP_TOOLS: LangChain wrappers
│   ├── mcp_client.py              # MCP stdio client
│   ├── mcp_server.py              # MCP server: weather, places, calendar
│   ├── itinerary_models.py        # StructuredItinerary Pydantic models
│   └── agent_schemas.py           # Agent-specific API schemas
│
└── knowledge/
    └── data/faqs.json             # Travel FAQs ingested into ChromaDB

tests/
├── test_agent.py                  # Unit tests: state, tools, validation
└── test_agent_integration.py      # End-to-end workflow tests

scripts/
└── ingest_knowledge.py            # Load FAQs into ChromaDB
```

---

## API Overview

All endpoints except `/auth/register` and `/auth/login` require a Bearer token.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Get JWT token |
| GET | `/users/me` | Current user profile |
| POST | `/trips/` | Create a trip |
| GET | `/trips/` | List user trips |
| GET | `/trips/{id}` | Get trip |
| PUT | `/trips/{id}` | Update trip |
| DELETE | `/trips/{id}` | Delete trip |
| GET | `/itineraries/{trip_id}` | Get saved itinerary |
| POST | `/agent/plan` | Generate itinerary (multimodal) |
| POST | `/agent/review` | Approve or revise draft |

Full interactive docs: **http://localhost:8000/docs**

---

---

# ⭐ Phase 6 — Multimodal AI & MCP

> This section covers Phase 6 requirements.
> Endpoints are live at **http://localhost:8000/docs** under the `agent` tag.

---

## 6.1 Multimodal Input/Output

The `/agent/plan` endpoint accepts three optional input modalities alongside the required `trip_id`:

| Field | Type | Description |
|-------|------|-------------|
| `trip_id` | Form field (int) | ID of the trip to plan |
| `text` | Form field (string, optional) | Plain text planning instructions |
| `audio` | File upload (optional) | Voice request — any format (MP3, WAV, M4A, OGG) |
| `image` | File upload (optional) | Destination photo for context extraction |

All three are normalized into a single text message before the agent runs.

### Speech-to-Text

- Library: `SpeechRecognition` + `pydub`
- Engine: Google free web speech API — **no API key, no billing**
- `pydub` converts any audio format to PCM WAV via ffmpeg before recognition
- File: `app/services/multimodal_service.py` → `transcribe_audio()`

### Image Understanding

- Model: `claude-haiku-4-5` via Anthropic vision API
- Detects image format from magic bytes (JPEG, PNG, GIF, WebP)
- Extracts: location clues, landmarks, climate indicators
- Output is appended to the text context sent to the planning agent
- File: `app/services/multimodal_service.py` → `analyze_image()`

### Text-to-Speech

- Provider: ElevenLabs (`Rachel` voice)
- Requires `ELEVENLABS_API_KEY` in `.env`
- Returns `audio_base64` field in the response (base64-encoded MP3)
- Non-blocking: if TTS fails or key is missing, the itinerary is still returned
- File: `app/services/multimodal_service.py` → `text_to_speech()`

---

## 6.2 MCP (Model Context Protocol)

MCP connects the AI agent to external travel tools in a clean, protocol-defined way. The server exposes tools over stdio; the client spawns it as a subprocess and communicates via the MCP protocol with a proper `session.initialize()` handshake.

### MCP Server — `app/agent/mcp_server.py`

Exposes 4 tools across 3 travel domains (weather, maps, calendar):

| Tool | Domain | Description | Data Source |
|------|--------|-------------|-------------|
| `get_weather` | Weather | 7-day forecast for any destination | Open-Meteo API (free) |
| `find_places` | Maps | Restaurants, hotels, museums near destination | OpenStreetMap Overpass API (free) |
| `check_calendar` | Calendar | Check vacation calendar for date conflicts | In-process calendar store |
| `add_to_calendar` | Calendar | Add an activity to the vacation calendar | In-process calendar store |

Geocoding (city name → lat/lon) uses the Open-Meteo geocoding API.

### MCP Client — `app/agent/mcp_client.py`

Uses the correct MCP protocol pattern with `session.initialize()` handshake:

```python
async with stdio_client(StdioServerParameters(...)) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()          # required MCP handshake
        result = await session.call_tool(tool_name, arguments)
```

### MCP Tools (LangChain wrappers) — `app/agent/mcp_tools.py`

Six `@tool` decorated async functions the LLM can call:
`get_weather_mcp`, `find_restaurants_mcp`, `find_hotels_mcp`, `find_museums_mcp`, `check_calendar_mcp`, `add_to_calendar_mcp`

---

## 6.3 LLM Integration

| Component | Model | Provider | Purpose |
|-----------|-------|----------|---------|
| Planning agent | `claude-haiku-4-5` | Anthropic | Itinerary generation + tool orchestration |
| Image analysis | `claude-haiku-4-5` | Anthropic | Vision — destination image understanding |

Tools are bound with `llm.bind_tools(ALL_TOOLS)` where `ALL_TOOLS = AGENT_TOOLS + MCP_TOOLS`.

---

## 6.4 End-to-End Flow

```
POST /agent/plan  (multipart/form-data)
  │
  ├── [audio] → pydub decode → SpeechRecognition → text
  ├── [image] → Claude vision → location summary → appended to text
  │
  ▼
LangGraph agent
  ├── calls MCP tools (weather, places, calendar)
  ├── calls AGENT_TOOLS (direct weather, RAG knowledge base)
  └── returns structured JSON itinerary
  │
  ▼
Response
  ├── itinerary (JSON)
  └── audio_base64 (ElevenLabs TTS, if key configured)

POST /agent/review  { action: "approve" | "revise" }
  ├── approve → saves to DB via itinerary_service
  └── revise  → re-runs agent with feedback, returns new draft
```

---

## 6.5 LangGraph Workflow

```
Client
  │
  ▼
FastAPI Routers
  │
  └── Agent (LangGraph)
        │
        ├── retrieve_trip_node  (authorization + DB load, runs before graph)
        │
        ├── agent_node  ──► ToolNode ──► agent_node (loop, max 5 iterations)
        │                     │
        │                     ├── AGENT_TOOLS
        │                     │     ├── weather_tool (Open-Meteo direct)
        │                     │     └── search_travel_knowledge_tool (ChromaDB RAG)
        │                     │
        │                     └── MCP_TOOLS (via MCP stdio client)
        │                           ├── get_weather_mcp
        │                           ├── find_restaurants/hotels/museums_mcp
        │                           ├── check_calendar_mcp
        │                           └── add_to_calendar_mcp
        │
        └── validate_node ──► END
```

State is checkpointed to SQLite after every step via `SqliteSaver`, enabling the revision workflow.

---

---

# Project Evolution — Phases 1–5

## Phase 1 — Python & FastAPI

Built the initial backend API with full CRUD for Users, Trips, and Itineraries.

**Key additions:**
- FastAPI REST API with Swagger/OpenAPI docs
- SQLAlchemy ORM with SQLite
- Pydantic schemas for request/response validation
- JWT authentication and protected routes
- Background tasks support

```
User → FastAPI → Database → Trip / Itinerary
```

---

## Phase 2 — LLM Foundations & Prompting

Replaced manual itinerary creation with AI-generated itineraries.

**Key additions:**
- LLM API integration (Anthropic Claude)
- System and user prompt design
- Trip details (destination, days, budget, style) used as prompt input
- Generated itinerary saved to database and returned via API

```
User → FastAPI → Trip details → LLM → Generated itinerary → Database
```

---

## Phase 3 — Designing AI Systems

Made AI responses reliable and structured.

**Key additions:**
- Structured JSON output from the LLM
- Pydantic validation of AI-generated responses
- Error handling and retry logic for invalid LLM output
- External weather tool integration (Open-Meteo)

```
Trip details → LLM + Weather Tool → Structured Output → Validation → Database
```

---

## Phase 4 — RAG & Knowledge Systems

Gave the planner access to a dedicated travel knowledge base.

**Key additions:**
- ChromaDB vector store
- Sentence-transformer embeddings
- Travel FAQs and destination info ingested via `scripts/ingest_knowledge.py`
- Semantic search retrieves relevant context before LLM call

```
Trip / Query → Embedding → ChromaDB → Relevant Context → LLM → Response
```

---

## Phase 5 — Frameworks & Orchestration

Upgraded from direct LLM calls to a tool-using AI agent.

**Key additions:**
- LangChain for LLM abstraction, tool definitions, and tool calling
- LangGraph for structured agent workflow and state management
- Agent decides which tools to call based on the request
- Weather and RAG tools available to the agent
- Approve/revise workflow with SQLite checkpointing

```
User Request → AI Agent → Tool selection → Tool execution → LLM → Final response
```

---

## Running Tests

```bash
uv run pytest tests/ -v
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework |
| `langgraph` | Agent workflow orchestration |
| `langchain-anthropic` | Claude integration |
| `mcp` | Model Context Protocol client + server |
| `chromadb` | Vector store for RAG |
| `sentence-transformers` | Embeddings for RAG |
| `SpeechRecognition` + `pydub` | Audio transcription |
| `elevenlabs` | Text-to-speech |
| `sqlalchemy` | ORM + SQLite persistence |
| `python-jose` | JWT authentication |
