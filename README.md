# Vacation Planner Backend API

## Overview

The Vacation Planner Backend API is a FastAPI-based backend service that allows users to create and manage vacation trips and itineraries.

The system provides authentication, trip management, and itinerary storage functionality using a RESTful API architecture.

---

# Features

## Authentication

* User registration
* User login
* JWT token authentication
* Protected profile endpoint

## Trip Management

* Create trips
* View all trips
* View a single trip
* Update trip details
* Delete trips

## Itinerary Management

* Create itineraries
* Store activities by day
* Retrieve itineraries for a trip

---

# Tech Stack

* Python
* FastAPI
* SQLAlchemy
* SQLite
* Pydantic
* JWT Authentication
* Uvicorn

---

# Project Structure

```text
AI_capstone_project/
│
├── app/
│   ├── routers/
│   │   ├── auth.py
│   │   ├── trips.py
│   │   └── itineraries.py
│   │
│   ├── __init__.py
│   ├── auth.py
│   ├── crud.py
│   ├── database.py
│   ├── dependencies.py
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── storage.py
│   └── tasks.py
│
├── .gitignore
|──  .env.example
├── requirements.txt
└── vacation_planner.db
```

---

# Architecture Explanation

The application follows a modular FastAPI architecture.

## Routers

The `routers/` directory contains API endpoints grouped by functionality:

* `auth.py` handles authentication
* `trips.py` handles trip CRUD operations
* `itineraries.py` handles itinerary operations

## Models

`models.py` defines SQLAlchemy database tables for:

* User
* Trip
* Itinerary

## Schemas

`schemas.py` contains Pydantic models for request validation and response serialization.

## CRUD Layer

`crud.py` contains database query logic and separates database operations from route handlers.

## Authentication

`auth.py` handles:

* Password hashing
* JWT token generation
* Token verification

## Database

`database.py` configures:

* SQLAlchemy engine
* Database sessions
* Base model

## Dependencies

`dependencies.py` contains reusable FastAPI dependencies such as authenticated user retrieval.

---

# Installation & Setup

## 1. Clone the Repository

```bash
git clone <repository_url>
cd AI_capstone_project
```

## 2. Create Virtual Environment

```bash
python -m venv .venv
```

## 3. Activate Virtual Environment

### Windows

```bash
.venv\Scripts\activate
```

### Linux/Mac

```bash
source .venv/bin/activate
```

## 4. Install Dependencies

```bash
pip install -r requirements.txt
```

## 5. Run the Application

```bash
uvicorn app.main:app --reload
```

The server will start at:

```text
http://127.0.0.1:8000
```

---

# API Documentation

FastAPI automatically provides Swagger documentation.

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

Alternative ReDoc documentation:

```text
http://127.0.0.1:8000/redoc
```

---

# Example Endpoints

## Authentication

```http
POST /auth/register
POST /auth/login
GET /users/me
```

## Trips

```http
POST /trips
GET /trips
GET /trips/{id}
PUT /trips/{id}
DELETE /trips/{id}
```

## Itineraries

```http
POST /itineraries
GET /itineraries/{trip_id}
POST /itineraries/generate/{trip_id}
GET /itineraries/status/{trip_id}
```

