from typing import Dict, Any
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

task_results: Dict[str, Dict[str, Any]] = {}

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