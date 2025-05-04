"""Game logic and routes for the rogue-like game."""
import random
from datetime import datetime
from typing import Tuple

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select, delete

from app.auth import get_current_user
from app.database import get_session
from app.models import MapTile, User, Mob, InventoryItem

router = APIRouter(prefix="/game", tags=["game"])


class MoveDirection(BaseModel):
    """Direction model for player movement."""
    direction: str


def is_adjacent(x1: int, y1: int, x2: int, y2: int) -> bool:
    """Check if two coordinates are adjacent."""
    return (abs(x1 - x2) + abs(y1 - y2)) == 1


def move_towards(
    start_x: int,
    start_y: int,
    target_x: int,
    target_y: int,
    db: Session,
    user: User
) -> Tuple[int, int]: # pylint: disable=too-many-arguments
    """Calculate next step towards target coordinates avoiding walls."""
    dx = target_x - start_x
    dy = target_y - start_y
    new_x, new_y = start_x, start_y

    if dx != 0:
        new_x += 1 if dx > 0 else -1
    elif dy != 0:
        new_y += 1 if dy > 0 else -1

    if (new_x, new_y) == (user.x, user.y):
        return start_x, start_y

    # Checking for a wall in the way
    tile = db.exec(select(MapTile).where(
        MapTile.x == new_x,
        MapTile.y == new_y,
        MapTile.user_id == user.id
    )).first()

    return (new_x, new_y) if tile and tile.tile_type != "wall" else (start_x, start_y)


def _handle_player_death(db: Session, user: User) -> dict:
    """Handle player death logic."""
    user.is_active = False
    db.execute(delete(InventoryItem).where(InventoryItem.owner_id == user.id))
    db.commit()
    generate_map(db=db, user=user)
    reset_player(db=db, user=user)
    return {
        "game_over": True,
        "status": "lose",
        "message": "You died!",
        "killed_mobs": user.killed_mobs,
        "inventory": 0
    }


def _handle_mob_attack(user: User, mob: Mob, db: Session) -> bool:
    """Process mob attack and return if player was attacked."""
    total_attack = user.base_attack + user.bonus_attack
    mob.health -= total_attack

    if mob.health <= 0:
        user.killed_mobs += 1
        apply_upgrades(user, db)
        db.add(InventoryItem(name="Mob Loot", owner_id=user.id, mob_id=mob.id))
        if random.random() < 0.2:
            db.add(InventoryItem(name="Стенолом", owner_id=user.id, quantity=1))
        db.delete(mob)

    db.add(user)
    db.commit()
    return True


def _move_mobs(db: Session, user: User) -> None:
    """Process mob movement and attacks."""
    mobs = db.exec(select(Mob).where(Mob.user_id == user.id)).all()
    for mob in mobs:
        new_mob_x, new_mob_y = move_towards(mob.x, mob.y, user.x, user.y, db, user)

        if is_adjacent(new_mob_x, new_mob_y, user.x, user.y):
            user.health -= 10
            if user.health <= 0:
                user.health = 0
                user.is_active = False
        else:
            mob.x, mob.y = new_mob_x, new_mob_y
            db.add(mob)


@router.post("/move")
def move_player(
    move_data: MoveDirection,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user)
) -> dict:
    """Move player and handle collisions, combat and game state."""
    if user.health <= 0:
        return _handle_player_death(db, user)

    if not user.is_active:
        raise HTTPException(400, "Game over!")

    direction = move_data.direction.lower()
    new_x, new_y = user.x, user.y
    attacked = False

    # Calculate new position
    match direction:
        case "up": new_y -= 1
        case "down": new_y += 1
        case "left": new_x -= 1
        case "right": new_x += 1
        case _: raise HTTPException(400, "Invalid direction")

    # Check valid tile
    tile = db.exec(select(MapTile).where(
        MapTile.x == new_x,
        MapTile.y == new_y,
        MapTile.user_id == user.id
    )).first()

    if not tile or tile.tile_type == "wall":
        raise HTTPException(400, "Invalid move")

    # Combat logic
    target_mob = db.exec(select(Mob).where(
        Mob.x == new_x,
        Mob.y == new_y,
        Mob.user_id == user.id
    )).first()

    if target_mob:
        attacked = _handle_mob_attack(user, target_mob, db)

    # Update player position if no attack
    if not attacked:
        user.x, user.y = new_x, new_y
        user.last_action = datetime.now()
        db.add(user)

    # Mob AI
    _move_mobs(db, user)
    db.commit()

    # Post-movement checks
    if user.health <= 0:
        return _handle_player_death(db, user)

    # Exit condition
    exit_tile = db.exec(select(MapTile).where(
        MapTile.x == user.x,
        MapTile.y == user.y,
        MapTile.tile_type == "exit",
        MapTile.user_id == user.id
    )).first()

    if exit_tile:
        user.is_active = False
        inventory_count = db.query(InventoryItem).filter(
            InventoryItem.owner_id == user.id).count()
        db.commit()
        generate_map(db=db, user=user)
        reset_player(db=db, user=user)
        return {
            "game_over": True,
            "status": "win",
            "killed_mobs": user.killed_mobs,
            "inventory": inventory_count,
            "message": "Exit reached!"
        }

    return {
        "x": user.x,
        "y": user.y,
        "health": user.health,
        "mobs": [{"x": m.x, "y": m.y} for m in
                db.exec(select(Mob).where(Mob.user_id == user.id)).all()]
    }


@router.post("/reset")
def reset_player(
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user)
) -> dict:
    """Reset player to starting position."""
    user.x = 0
    user.y = 0
    user.health = 100 + user.bonus_health
    user.is_active = True
    db.commit()
    return {"message": "Player reset"}


@router.post("/generate_map")
def generate_map(
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user)
) -> dict:
    """Generate new game map with walls, exit and mobs."""
    db.execute(delete(MapTile).where(MapTile.user_id == user.id))
    db.execute(delete(Mob).where(Mob.user_id == user.id))
    db.add(InventoryItem(name="Стенолом", owner_id=user.id, quantity=1))
    db.commit()

    # Generate base map
    for x in range(20):
        for y in range(20):
            tile_type = "floor" if (x, y) in [(0, 0), (1, 0), (0, 1), (19, 19)] \
                else "wall" if random.random() < 0.2 else "floor"
            db.add(MapTile(
                x=x,
                y=y,
                tile_type=tile_type,
                user_id=user.id
            ))

    # Add exit
    db.add(MapTile(
        x=19,
        y=19,
        tile_type="exit",
        user_id=user.id
    ))

    # Add mobs
    mob_count = 0
    while mob_count < 5:
        x, y = random.randint(0, 19), random.randint(0, 19)
        tile = db.exec(select(MapTile)
                      .where(MapTile.x == x, MapTile.y == y, MapTile.user_id == user.id)
                      ).first()
        if tile and tile.tile_type != "wall":
            db.add(Mob(x=x, y=y, user_id=user.id, health=50))
            mob_count += 1

    db.commit()
    return {"message": "Персональная карта создана"}


@router.get("/state")
def get_game_state(
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user)
) -> dict:
    """Get current game state including player, mobs and tiles."""
    if not db.exec(select(MapTile).where(MapTile.user_id == user.id)).first():
        generate_map(db=db, user=user)
        reset_player(db=db, user=user)

    return {
        "player": {
            "x": user.x,
            "y": user.y,
            "health": user.health,
            "is_active": user.is_active
        },
        "mobs": [{"x": m.x, "y": m.y}
                for m in db.exec(select(Mob).where(Mob.user_id == user.id)).all()],
        "tiles": [{"x": t.x, "y": t.y, "type": t.tile_type}
                 for t in db.exec(select(MapTile).where(MapTile.user_id == user.id)).all()]
    }


@router.patch("/surrender")
def surrender(
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user)
) -> dict:
    """Handle player surrender."""
    user.health = 0
    user.is_active = False
    db.execute(delete(InventoryItem).where(InventoryItem.owner_id == user.id))
    db.commit()

    generate_map(db=db, user=user)
    reset_player(db=db, user=user)
    return {
        "game_over": True,
        "status": "lose",
        "message": "Вы сдались!",
        "killed_mobs": user.killed_mobs,
        "inventory": 0
    }


@router.put("/use-wallbreaker")
def use_wallbreaker(
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user)
) -> dict:
    """Use wallbreaker item to destroy nearby walls."""
    wallbreaker = db.exec(
        select(InventoryItem).where(
            InventoryItem.owner_id == user.id,
            InventoryItem.name == "Стенолом",
            InventoryItem.quantity >= 1
        )
    ).first()

    if not wallbreaker:
        raise HTTPException(400, "У вас нет стенолома!")

    exit_tile = db.exec(
        select(MapTile).where(
            MapTile.user_id == user.id,
            MapTile.tile_type == "exit"
        )
    ).first()
    if not exit_tile:
        raise HTTPException(400, "Выход не найден")

    def get_walls_around(x: int, y: int) -> list:
        """Get walls in 3x3 area around coordinates."""
        walls = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                check_x = x + dx
                check_y = y + dy
                if 0 <= check_x < 20 and 0 <= check_y < 20:
                    tile = db.exec(select(MapTile).where(
                        MapTile.x == check_x,
                        MapTile.y == check_y,
                        MapTile.user_id == user.id,
                        MapTile.tile_type == "wall"
                    )).first()
                    if tile:
                        walls.append(tile)
        return walls

    # Get walls around player and exit
    walls_to_destroy = get_walls_around(user.x, user.y) + get_walls_around(exit_tile.x, exit_tile.y)
    unique_walls = {(wall.x, wall.y): wall for wall in walls_to_destroy}
    unique_walls.pop((exit_tile.x, exit_tile.y), None)

    if not unique_walls:
        raise HTTPException(400, "Нет стен для разрушения")

    # Update walls and inventory
    for wall in unique_walls.values():
        wall.tile_type = "floor"
        db.add(wall)

    wallbreaker.quantity -= 1
    if wallbreaker.quantity == 0:
        db.delete(wallbreaker)
    else:
        db.add(wallbreaker)

    db.commit()
    return {"message": f"Уничтожено {len(unique_walls)} стен!"}


def apply_upgrades(user: User, db: Session) -> None:
    """Apply stat upgrades when reaching kill milestones."""
    next_level = 2 ** user.upgrade_level
    if user.killed_mobs >= next_level:
        user.upgrade_level += 1
        user.bonus_attack += 5
        user.bonus_health += 20
        user.health += user.bonus_health
    db.add(user)
    db.commit()


@router.get("/upgrades")
def get_upgrades(user: User = Depends(get_current_user)) -> dict:
    """Get player upgrade progression."""
    next_level = 2 ** user.upgrade_level
    return {
        "killed_mobs": user.killed_mobs,
        "bonus_attack": user.bonus_attack,
        "bonus_health": user.bonus_health,
        "next_level": next_level
    }
