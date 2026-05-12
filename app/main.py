from fastapi import FastAPI
from routers import trip

app = FastAPI(
    title="AI Vacation planner",
    description="A FAST API for an AI to help plan for vacations"
)

app.include_router(trip.router)

@app.get("/")
async def root():
    return {
        "Message": "Welcome to the AI Vacation Planner API",
        "documentation": "/docs",
        "endpoints": {
            "POST /trips": "Create a trip",
            "GET /trips": "Get all trips",
            "PUT /trips/{id}": "Update a trip",
            "DELETE /trips/{id}": "Delete a trip"
        }
    }



