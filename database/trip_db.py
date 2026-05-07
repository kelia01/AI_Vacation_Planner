from typing import Dict

trips_db: Dict[int, dict] = {}

trip_id_counter = 1

def get_next_id() -> int:
    global trip_id_counter
    current_id = trip_id_counter
    trip_id_counter += 1
    return current_id

def save_trip(trip_data: Dict) -> dict:
    trip_id = get_next_id()
    trip_data["id"] = trip_id
    trips_db[trip_id] = trip_data
    trip_data["message"] = "Trip created successfully"
    return trip_data

def get_all_trips() -> list:
    return list(trips_db.values())

def get_trip_by_id(trip_id: int) -> dict | None:
    return trips_db.get(trip_id)

def update_trip_by_id(trip_id: int, updated_data: dict) -> dict | None:
    if trip_id not in trips_db:
        return None

    original_trip = trips_db[trip_id]
    updated_trip = {
        **original_trip,
        **updated_data,
        "id": trip_id,
    }

    trips_db[trip_id] = updated_trip
    return updated_trip

def delete_trip_by_id(trip_id: int) -> bool:
    if trip_id in trips_db:
        del trips_db[trip_id]
        return True
    return False