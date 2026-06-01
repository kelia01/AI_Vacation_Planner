from fastapi import APIRouter, Depends
from app import schemas, models, dependencies

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=schemas.UserResponse)
async def get_current_user_profile(
        current_user: models.User = Depends(dependencies.get_current_user)
):
    return current_user