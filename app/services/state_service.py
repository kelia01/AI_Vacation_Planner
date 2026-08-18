import json


def build_state(trip, itinerary=None):

    state = f"""

Destination:
{trip.destination}

Days:
{trip.days}

Budget:
{trip.budget}

Travel Style:
{trip.trip_style}

"""

    if itinerary:

        state += "\nCurrent itinerary:\n"

        for day in itinerary.days:

            activities = json.loads(day.activities)

            state += f"\nDay {day.day_number}\n"

            for activity in activities:

                state += f"- {activity}\n"

    return state