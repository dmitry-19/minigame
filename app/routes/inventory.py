"""Inventory management endpoints."""
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.models import InventoryItem, User
from app.database import get_session
from app.auth import get_current_user

router = APIRouter()

@router.get("/inventory")
def get_inventory(
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user)
)-> dict:
    """Get player's inventory items."""
    items = db.exec(select(InventoryItem)
                    .where(InventoryItem.owner_id == user.id)).all()
    return {"items": items}
