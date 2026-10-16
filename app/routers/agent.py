import base64
import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.agent import run_agent, StructuredItinerary
from app.services import trip_service, itinerary_service
from app.services.multimodal_service import transcribe_audio, analyze_image, text_to_speech
from app import schemas
from app.agent.agent_schemas import ReviewRequest, ReviewResponse

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/plan")
async def plan_itinerary(
    trip_id: int = Form(...),
    text: Optional[str] = Form(None),
    audio: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Plan itinerary — accepts text, voice (WAV/MP3), or destination image."""

    try:
        trip_service.get_trip_by_id(db, trip_id, current_user.id)
    except HTTPException:
        raise HTTPException(status_code=404, detail="Trip not found")

    parts = []
    if text:
        parts.append(f"Instructions: {text}")
    
    if audio:
        audio_bytes = await audio.read()
        if audio_bytes:
            transcript = transcribe_audio(audio_bytes)
            parts.append(f"Voice request: {transcript}")

    if image:
        image_bytes = await image.read()
        content_type = image.content_type  # pass real content-type to avoid hardcoded jpeg
        if image_bytes:
            image_context = analyze_image(image_bytes, content_type=content_type)
            parts.append(f"Image context: {image_context}")

    combined_text = "\n".join(parts) if parts else "Plan my trip"

    thread_id = f"trip_{trip_id}_user_{current_user.id}_{uuid.uuid4().hex[:8]}"

    agent_state = await run_agent(
        trip_id=trip_id,
        user_id=current_user.id,
        message=combined_text,
        thread_id=thread_id,
        db=db,
    )

    if agent_state.get("error"):
        return {"status": "error", "thread_id": thread_id, "error": agent_state["error"]}

    itinerary = agent_state.get("itinerary_draft")

    audio_b64 = None
    tts_audio = text_to_speech(f"Your itinerary for {itinerary.get('metadata', {}).get('destination', 'your trip')} is ready.")
    if tts_audio:
        audio_b64 = base64.b64encode(tts_audio).decode()

    return {
        "status": "success",
        "thread_id": thread_id,
        "itinerary": itinerary,
        "audio_base64": audio_b64,
    }


@router.post("/review", response_model=ReviewResponse, status_code=status.HTTP_200_OK)
async def review_itinerary(
    request: ReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve (save) or revise the draft itinerary."""

    try:
        parts = request.thread_id.split("_")
        trip_id = int(parts[1])
    except (IndexError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid thread_id format")

    try:
        trip_service.get_trip_by_id(db, trip_id, current_user.id)
    except HTTPException:
        raise HTTPException(status_code=404, detail="Trip not found")

    if request.action == "approve":
        try:
            structured = StructuredItinerary(**request.itinerary_data)
            legacy_format = structured.to_legacy_format()
            legacy_format["trip_id"] = trip_id
            itinerary_create = schemas.ItineraryCreate(**legacy_format)
            db_itinerary = itinerary_service.create_itinerary(db, itinerary_create, current_user.id)
            return ReviewResponse(status="success", thread_id=request.thread_id, saved_id=db_itinerary.id)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=f"Invalid itinerary: {e}")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save: {e}")

    elif request.action == "revise":
        try:
            agent_state = await run_agent(
                trip_id=trip_id,
                user_id=current_user.id,
                message="",
                thread_id=request.thread_id,
                db=db,
                user_feedback=request.feedback,
            )
            if agent_state.get("error"):
                return ReviewResponse(status="error", thread_id=request.thread_id, error=agent_state["error"])
            return ReviewResponse(
                status="success",
                thread_id=request.thread_id,
                itinerary=agent_state.get("itinerary_draft"),
            )
        except Exception as e:
            return ReviewResponse(status="error", thread_id=request.thread_id, error=f"Revision failed: {e}")

    raise HTTPException(status_code=400, detail="Invalid action. Use 'approve' or 'revise'")
