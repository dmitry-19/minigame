# Authentication routes for user registration, login, and account deletion.
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlmodel import Session, select, delete

from app.models import User, InventoryItem, MapTile, Mob
from app.schemas import UserCreate, Token, UserResponse
from app.database import get_session
from app.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
)
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_session)):
    """Register a new user with username and password."""
    existing_user = db.exec(
        select(User).where(User.username == user.username)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    hashed_password = get_password_hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    return db_user


@router.post("/login", response_model=Token)
def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_session),
):
    """Authenticate user and return access token."""
    user = db.exec(select(User).where(User.username == username)).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.delete("/delete-account")
def delete_user(
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Delete user account and all associated data."""
    db.execute(delete(InventoryItem).where(InventoryItem.owner_id == user.id))
    db.execute(delete(MapTile).where(MapTile.user_id == user.id))
    db.execute(delete(Mob).where(Mob.user_id == user.id))
    db.delete(user)
    db.commit()
    return {"message": "Аккаунт удален"}
