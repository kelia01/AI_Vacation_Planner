from fastapi import HTTPException, status, Depends, APIRouter
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from schema import schemas
import crud
from database import db

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(db.get_db())):
    if crud.get_user_by_email(db, user.username):
        

