# AI Vacation Planner

An intelligent backend service for planning trips using conversational AI, structured itinerary generation, external tools, and travel knowledge retrieval.

## Project Overview

The AI Vacation Planner is a FastAPI-based backend that allows users to create trips and itineraries and use an LLM to automatically generate travel plans based on trip information stored in the database.

## Current Features

### Backend API

* FastAPI REST API
* SQLite database
* SQLAlchemy/ORM-based database operations
* Pydantic request and response schemas
* CRUD operations for trips and itineraries
* JWT-based authentication
* Environment-based configuration
* Swagger/OpenAPI documentation

### Trip Management

Users can:

* Register
* Log in
* View their profile
* Create trips
* View all their trips
* View individual trips
* Update trip details
* Delete trips

A trip contains information such as:

* Destination
* Number of days
* Budget
* Travel style

### Itinerary Management

Users can:

* Create an itinerary manually
* Retrieve an itinerary for a trip
* Generate an itinerary using AI
* Store generated itineraries in the database

## AI Itinerary Generation

The backend integrates with the Anthropic API to generate itineraries from trip information stored in the database.

The AI receives information such as:

* Destination
* Number of days
* Budget
* Travel style

The generated itinerary is expected to follow a predictable structure:

```json
{
  "days": [
    {
      "day": 1,
      "activities": [
        "Breakfast",
        "Museum visit",
        "Dinner"
      ]
    }
  ]
}
```

The generated response is parsed from JSON and validated using Pydantic before being saved to the database.

## AI Generation Flow

```text
Client
  |
  v
POST /itineraries/generate/{trip_id}
  |
  v
FastAPI
  |
  v
Retrieve trip from database
  |
  v
Build AI prompt
  |
  v
Anthropic Claude
  |
  +------> Weather Tool
  |          |
  |          v
  |      Weather API
  |          |
  |          v
  |      Weather result
  |          |
  <----------+
  |
  v
Structured itinerary response
  |
  v
JSON parsing
  |
  v
Pydantic validation
  |
  v
Save itinerary
  |
  v
Return JSON response
```

## Structured Output and Validation

The AI response is not treated as trusted plain text.

The backend:

1. Requests a structured itinerary from the LLM.
2. Extracts the text response.
3. Parses the response using Python's JSON parser.
4. Validates the resulting data using Pydantic.
5. Associates the validated itinerary with the user's trip.
6. Saves the result to the database.

This reduces the risk of storing malformed or unusable AI-generated data.

## Retry Handling

If Claude returns a response that cannot be parsed as valid JSON, the backend retries the generation request and instructs the model to return only the required JSON structure.

This provides a basic recovery mechanism for invalid LLM output.

## External Tool Integration

The AI itinerary generator includes a weather lookup tool.

Claude can request the `get_weather` tool before generating an itinerary.

The tool flow is:

```text
Claude
  |
  | tool_use
  v
get_weather(destination)
  |
  v
Weather service
  |
  v
Weather result
  |
  v
Claude
  |
  v
Final itinerary
```

The backend executes the requested function and sends the result back to Claude as a tool result.

This allows the AI generation process to use external, real-time information rather than relying entirely on the model's internal knowledge.

## API Documentation

The FastAPI application provides interactive Swagger/OpenAPI documentation.

When the backend is running, the documentation is available at:

```text
http://127.0.0.1:8000/docs
```

The raw OpenAPI specification is available at:

```text
http://127.0.0.1:8000/openapi.json
```

## Main API Endpoints

### Authentication

```text
POST /auth/register
POST /auth/login
GET  /users/me
```

### Trips

```text
POST   /trips
GET    /trips
GET    /trips/{id}
PUT    /trips/{id}
DELETE /trips/{id}
```

### Itineraries

```text
POST /itineraries
GET  /itineraries/{trip_id}
POST /itineraries/generate/{trip_id}
```

The exact request and response schemas are documented automatically through Swagger.

## Example Trip

### Request

```json
{
  "destination": "Paris",
  "days": 5,
  "budget": 1500,
  "trip_style": "budget"
}
```

### Response

```json
{
  "id": 1,
  "destination": "Paris",
  "days": 5,
  "budget": 1500,
  "trip_style": "budget",
  "message": "Trip created successfully"
}
```

## Example Itinerary

```json
{
  "trip_id": 1,
  "itinerary": [
    {
      "day": 1,
      "activities": [
        "Eiffel Tower",
        "Seine River Walk"
      ]
    },
    {
      "day": 2,
      "activities": [
        "Louvre Museum",
        "Montmartre"
      ]
    }
  ],
  "message": "Itinerary created successfully"
}
```

## Project Structure

The project follows a modular FastAPI structure.

```text
AI_capstone_project/
│
├── app/
│   ├── main.py
│   ├── crud.py
│   ├── schemas.py
│   │
│   ├── models/
│   │
│   ├── routers/
│   │
│   └── services/
│       ├── ai_service.py
│       └── weather_service.py
│
├── .env
├── requirements.txt
├── vacation_planner.db
└── README.md
```

## Environment Configuration

Create a `.env` file in the project root:

```env
DATABASE_URL=sqlite:///./vacation_planner.db

SECRET_KEY=your-secret-key

ANTHROPIC_API_KEY=your-anthropic-api-key

ALGORITHM=HS256
```

Do not commit `.env` or API keys to GitHub.

Add the environment file to `.gitignore`:

```text
.env
```

## Installation

Clone the repository and navigate into the project:

```bash
git clone <repository-url>
cd AI_capstone_project
```

Create a virtual environment:

### Windows

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure the `.env` file with the required database, authentication, and Anthropic API settings.

## Running the Application

Start the FastAPI development server:

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

## Development Progress

### Phase 1 — Python & FastAPI

Implemented:

* FastAPI backend
* REST API
* SQLite database
* ORM/database operations
* User, Trip, and Itinerary entities
* CRUD operations
* Authentication
* Pydantic schemas
* Environment configuration
* Swagger/OpenAPI documentation

### Phase 2 — LLM Foundations & Prompting

Implemented:

* Anthropic Claude integration
* System and user prompts
* Prompt construction using database trip information
* AI-generated itineraries
* Saving generated itineraries to the database
* JSON response generation

### Phase 3 — Designing AI Systems

Implemented:

* Structured itinerary output
* JSON parsing
* Pydantic validation
* Retry handling for invalid JSON
* External weather tool
* Tool-call handling
* State maintained during the tool-call interaction
* AI-generated itinerary persistence
* Swagger documentation updates

## Technology Stack

### Backend

* Python
* FastAPI
* Pydantic
* SQLAlchemy
* SQLite

### AI

* Anthropic API
* Claude Haiku
* Prompt engineering
* Structured JSON generation
* Tool calling

### Authentication

* JWT
* Password hashing

### Development

* Git
* GitHub
* Swagger/OpenAPI
* Python virtual environments

## Architecture

The current backend architecture separates API handling, database operations, AI functionality, and external services.

```text
                    Client
                      |
                      v
                  FastAPI
                      |
          +-----------+-----------+
          |                       |
          v                       v
     Authentication          API Routers
                                  |
                         +--------+--------+
                         |                 |
                         v                 v
                       CRUD          AI Service
                         |                 |
                         v                 +------> Anthropic
                     Database              |
                                           +------> Weather Service
```

The next major development stage is **RAG and Knowledge Systems**, where the AI will be given access to a dedicated travel knowledge base and will retrieve relevant information before generating itineraries.
