from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app import schemas, database
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate,
             background_tasks: BackgroundTasks,
             db: Session = Depends(database.get_db)):
    
    return auth_service.register_user(db, user, background_tasks)

@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):

    return auth_service.login_user(db, form_data)
