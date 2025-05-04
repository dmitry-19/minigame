"""Pydantic schemas for data validation."""
from pydantic import BaseModel

class UserCreate(BaseModel):
    """User registration data."""
    username: str
    password: str

class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    """User data response."""
    id: int
    username: str
    x: int = 0
    y: int = 0
    health: int
    is_active: bool = True
