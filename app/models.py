"""Database models for the game."""
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship

class User(SQLModel, table=True, extend_existing=True):
    """Player account model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str
    x: int = 0
    y: int = 0
    bonus_health: int = 0
    health: int = Field(default=100)
    base_attack: int = 10
    bonus_attack: int = 0
    killed_mobs: int = 0
    upgrade_level: int = 0
    is_active: bool = True
    last_action: Optional[datetime] = None
    inventory: list["InventoryItem"] = Relationship(back_populates="owner")

class InventoryItem(SQLModel, table=True):
    """Player inventory item model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    quantity: int = 1
    owner_id: int = Field(foreign_key="user.id")
    mob_id: Optional[int] = Field(foreign_key="mob.id", default=None)
    owner: User = Relationship(back_populates="inventory")

class MapTile(SQLModel, table=True):
    """Game map tile model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    x: int
    y: int
    tile_type: str
    user_id: int = Field(foreign_key="user.id")

class Mob(SQLModel, table=True):
    """Enemy entity model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    x: int
    y: int
    health: int = 50
    user_id: int = Field(foreign_key="user.id")
