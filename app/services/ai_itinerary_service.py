from dotenv import load_dotenv
load_dotenv()

import json, os
from anthropic import Anthropic
from fastapi import HTTPException
from app import crud, schemas

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-haiku-4-5"

def generate_itinerary_from_trip(trip):

    prompt = f"""Create a realistic {trip.days}-day itinerary for {trip.destination}.

Budget: {trip.budget}
Trip style: {trip.trip_style}

Requirements:
- Only include places within {trip.destination}
- Stay within the budget
- Create activities for every day
- Activities should be realistic
- Avoid impossible travel times
"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system="You are a travel planner. Respond with ONLY raw valid JSON. "
               "No markdown, no code fences, no explanation. "
               "Schema: {\"days\": [{\"day\": 1, \"activities\": [\"activity1\"]}]}",
        messages=[{"role": "user", "content": prompt},
                  {"role": "assistant", "content": "{"}],
        stop_sequences=["```"]
    )

    answer = "{" + response.content[0].text

    try:
        return json.loads(answer)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI returned invalid JSON: {str(e)} — raw: {answer[:200]}"
        )
    
def generate_ai_itinerary(db, trip_id, user_id):
    trip = crud.get_trip_by_id(db, trip_id, user_id)

    if not trip:
        raise HTTPException(
            status_code=404,
            detail="Trip not found"
        )

    ai_data = generate_itinerary_from_trip(trip)

    itinerary_schema = schemas.ItineraryCreate(
        trip_id = trip.id,
        days = ai_data["days"]
    )

    return crud.create_itinerary(db, itinerary_schema, user_id)
