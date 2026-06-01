
from fastapi import HTTPException
from app import crud, tasks, auth

def register_user(db, user, background_tasks):
    if crud.get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    if crud.get_user_by_username(db, user.username):
        raise HTTPException(status_code=400, detail="Username already taken")

    new_user = crud.create_user(db, user)

    background_tasks.add_task(
        tasks.send_welcome_email_background,
        email=new_user.email,
        username=new_user.username
    )

    return new_user

def login_user(db, form_data):
    user = crud.get_user_by_email(db, form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}