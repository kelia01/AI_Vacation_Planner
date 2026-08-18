from dotenv import load_dotenv
load_dotenv()

import json, os
from anthropic import Anthropic
from fastapi import HTTPException
from app import crud, schemas
from app.services.weather_service import get_weather

api_key = os.getenv("ANTHROPIC_API_KEY")
MODEL = "claude-haiku-4-5"
client = Anthropic(api_key=api_key)

TOOLS = [
    {
        "name": "get_weather",
        "description": (
            "Get the weather for a travel destination before creating an itinerary."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "description": "Destination city or country"
                }
            },
            "required": ["destination"]
        }
    }
]

def _execute_tool(tool_name: str, tool_input: dict):

    if tool_name == "get_weather":
        return get_weather(tool_input["destination"])

    raise ValueError(f"Unknown tool: {tool_name}")

def _validate_itinerary(ai_data):

    try:

        return schemas.ItineraryCreate(
            trip_id=0,
            days=ai_data["days"]
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Invalid itinerary generated: {e}"
        )
        
def generate_itinerary_from_trip(trip):

    prompt = f"""
You are planning a vacation.

Destination:
{trip.destination}

Number of days:
{trip.days}

Budget:
{trip.budget}

Travel style:
{trip.trip_style}

Instructions:

1. Use the weather tool first.

2. Create activities only inside the destination.

3. Respect the travel style.

4. Stay within budget.

5. Every day must contain at least three activities.

6. Return ONLY valid JSON.

Required schema:

{{
    "days":[
        {{
            "day":1,
            "activities":[
                "Breakfast",
                "Museum",
                "Dinner"
            ]
        }}
    ]
}}
"""

    messages = [
        {
            "role": "user",
            "content": prompt
        }
    ]

    retries = 2

    while retries >= 0:

        response = client.messages.create(
            model=MODEL,
            max_tokens=1200,
            system=(
                "You are an expert travel planner. "
                "Always use the weather tool before planning. "
                "Return only valid JSON."
            ),
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "tool_use":

            tool_use = next(
                block
                for block in response.content
                if block.type == "tool_use"
            )
            print("=== TOOL CALL ===")
            print("Tool:", tool_use.name)
            print("Input:", tool_use.input)
            print("=================")

            result = _execute_tool(
                tool_use.name,
                tool_use.input
            )
            print("=== TOOL RESULT ===")
            print(result)
            print("===================")

            messages.append(
                {
                    "role": "assistant",
                    "content": response.content
                }
            )

            messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": json.dumps(result)
                        }
                    ]
                }
            )

            continue

        text = "".join(
            block.text
            for block in response.content
            if block.type == "text"
        )
        print("=== CLAUDE RESPONSE ===")
        print(text)
        print("======================")

        try:
            cleaned_text = text.strip()

            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[len("```json"):].strip()

            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[len("```"):].strip()

            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3].strip()

            return json.loads(cleaned_text)

        except json.JSONDecodeError:

            retries -= 1

            messages.append(
                {
                    "role": "assistant",
                    "content": response.content
                }
            )

            messages.append(
                {
                    "role": "user",
                    "content":
                        "The previous response was not valid JSON. "
                        "Return ONLY valid JSON."
                        "Do not use Markdown code fences. "
                        "Do not include explanations before or after the JSON."
                }
            )

    raise HTTPException(
        status_code=500,
        detail="Claude failed to produce valid JSON."
    )
    
def generate_ai_itinerary(db, trip_id, user_id):
    trip = crud.get_trip_by_id(db, trip_id, user_id)

    if not trip:
        raise HTTPException(
            status_code=404,
            detail="Trip not found"
        )

    try:
        ai_data = generate_itinerary_from_trip(trip)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI generation failed: {str(e)}"
        )

    validated = _validate_itinerary(ai_data)

    validated.trip_id = trip.id

    return crud.update_itinerary(
        db,
        validated,
        user_id
    )
