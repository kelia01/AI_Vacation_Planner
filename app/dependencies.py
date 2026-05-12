from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from auth import (verify_password, get_password_hash, create_access_token, decode_token)
from database import db


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(db.get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTPException_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )

    payload = decode_token(token)
    if not payload:
        raise credentials_exception

    email: str = payload.get("sub")
    if not email:
        raise credentials_exception

    user = crud.get_use_by_email(db, email)
    if not user:
        raise credentials_exception

    return user
