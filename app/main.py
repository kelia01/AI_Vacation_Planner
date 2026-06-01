from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from app.database import engine, Base
from app.routers import auth, users, trips, itineraries

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Vacation Planner",
    description="Intelligent Trip Planning Assistant",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(trips.router)
app.include_router(itineraries.router)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    schema.setdefault("components", {}).setdefault("securitySchemes", {})

    schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }

    }
    no_auth_routes = ["/auth/login", "/auth/register", "/", "/health"]

    for path, path_item in schema.get("paths", {}).items():
        for method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            if path in no_auth_routes:
                operation["security"] = []
            else:
                operation["security"] = [{"BearerAuth": []}]

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi

@app.get("/")
def root():
    return {
        "message": "AI Vacation Planner API",
        "version": "2.0.0",
        "features": [
            "User Authentication",
            "Trip CRUD",
            "Itinerary Management",
        ],
        "docs": "/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/test-background")
async def test_background_task(background_tasks: BackgroundTasks):
    background_tasks.add_task(
        lambda: print("This runs in the background!")
    )
    return {"message": "Background task started"}