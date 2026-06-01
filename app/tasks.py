from typing import Dict, Any
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

task_results: Dict[str, Dict[str, Any]] = {}


def generate_itinerary_background(trip_id: int, destination: str, days: int):
    task_id = f"trip_{trip_id}"

    try:
        logger.info(f"Starting itinerary generation for {destination}")

        time.sleep(5)

        itinerary = []
        for day in range(1, days + 1):
            itinerary.append({
                "day": day,
                "activities": [
                    f"Morning activity in {destination}",
                    f"Afternoon exploration of {destination}",
                    f"Evening dinner in {destination}"
                ]
            })

        task_results[task_id] = {
            "status": "completed",
            "result": {
                "trip_id": trip_id,
                "destination": destination,
                "days": days,
                "itinerary": itinerary
            }
        }
        logger.info(f"Itinerary generation completed for trip {trip_id}")

    except Exception as e:
        logger.error(f"Background task failed: {e}")
        task_results[task_id] = {
            "status": "failed",
            "error": str(e)
        }


def send_welcome_email_background(email: str, username: str):
    try:
        logger.info(f"Sending welcome email to {email}")
        time.sleep(2)
        logger.info(f"Welcome email sent to {username}")

        task_results[f"email_{email}"] = {
            "status": "completed",
            "message": f"Welcome email sent to {username}"
        }
    except Exception as e:
        logger.error(f"Email task failed: {e}")