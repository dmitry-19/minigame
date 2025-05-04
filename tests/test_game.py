import pytest
from sqlmodel import Session, select

from app.database import get_session
from app.models import User, MapTile, Mob, InventoryItem
from datetime import datetime, timedelta


# Фикстура для аутентифицированного пользователя
@pytest.fixture
def auth_token(client):
    # Регистрация
    client.post("/auth/register", json={"username": "testuser", "password": "testpass"})
    # Логин
    response = client.post(
        "/auth/login",
        data={"username": "testuser", "password": "testpass"}
    )
    return response.json()["access_token"]


def test_generate_map(client, auth_token):
    response = client.post(
        "/game/generate_map",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Персональная карта создана"


def test_initial_game_state(client, auth_token):
    response = client.get(
        "/game/state",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["player"]["x"] == 0
    assert data["player"]["y"] == 0
    assert data["player"]["health"] == 100
    assert len(data["mobs"]) == 5


def test_valid_movement(client, auth_token, session):
    user = session.exec(select(User)).first()
    session.add(MapTile(x=1, y=0, tile_type="floor", user_id=user.id))
    session.commit()
    client.post("/game/reset", headers={"Authorization": f"Bearer {auth_token}"})
    response = client.post(
        "/game/move",
        json={"direction": "right"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    assert response.json()["x"] == 1


def test_wall_collision(client, auth_token,session):

    user = session.exec(select(User)).first()
    session.add(MapTile(x=1, y=0, tile_type="wall", user_id=user.id))
    session.commit()

    response = client.post(
        "/game/move",
        json={"direction": "right"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 400
    assert "Invalid move" in response.json()["detail"]


def test_mob_attack(client, auth_token, session):
    user = session.exec(select(User)).first()
    session.add(user)
    user.base_attack = 50
    session.add(MapTile(x=1, y=0, tile_type="floor", user_id=user.id))
    session.add(Mob(x=1, y=0, user_id=user.id, health=50))
    session.commit()

    response = client.post(
        "/game/move",
        json={"direction": "right"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    assert user.killed_mobs != 0


def test_player_death(client, auth_token, session):

    user = session.exec(select(User)).first()
    user.health = 0
    session.add(user)
    session.commit()

    response = client.post(
        "/game/move",
        json={"direction": "right"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    assert response.json()["game_over"] == True
    assert response.json()["status"] == "lose"


def test_win_condition(client, auth_token, session):
    user = session.exec(select(User)).first()
    for x in range(19):
        session.add(MapTile(x=x, y=19, tile_type="floor", user_id=user.id))
    session.commit()
    session.add(MapTile(x=19, y=19, tile_type="exit", user_id=user.id))
    session.commit()
    user.x = 18
    user.y = 19
    session.add(user)
    session.commit()

    response = client.post(
        "/game/move",
        json={"direction": "right"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    assert response.json()["game_over"] == True
    assert response.json()["status"] == "win"


def test_surrender(client, auth_token):
    response = client.patch(
        "/game/surrender",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "lose"
    assert response.json()["message"] == "Вы сдались!"


def test_wallbreaker_destroys_walls(client, auth_token, session):
    # Добавляем стенолом в инвентарь
    user = session.exec(select(User)).first()
    session.add(InventoryItem(name="Стенолом", owner_id=user.id, quantity=1))
    session.commit()

    # Создаем стены вокруг игрока и выхода
    walls = [(0, 1), (1, 0), (1, 1), (19, 18), (18, 19)]
    for x, y in walls:
        session.add(MapTile(x=x, y=y, tile_type="wall", user_id=user.id))
    session.add(MapTile(x=19, y=19, tile_type="exit", user_id=user.id))  # Добавляем выход
    session.commit()

    # Используем стенолом
    response = client.put("/game/use-wallbreaker", headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 200

    # Проверяем разрушение стен
    destroyed = 0
    for x, y in walls:
        tile = session.exec(select(MapTile).where(
            MapTile.x == x,
            MapTile.y == y,
            MapTile.user_id == user.id
        )).first()
        if tile and tile.tile_type == "floor":
            destroyed += 1
    assert destroyed >= 3


def test_invalid_wallbreaker_use(client, auth_token):
    response = client.put(
        "/game/use-wallbreaker",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 400
    assert "У вас нет стенолома" in response.json()["detail"]


def test_player_reset(client, auth_token, session):
    user = session.exec(select(User)).first()
    user.x = 5
    user.y = 5
    session.add(user)
    session.commit()

    response = client.post(
        "/game/reset",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Player reset"

    # Проверяем сброс позиции
    state_response = client.get("/game/state", headers={"Authorization": f"Bearer {auth_token}"})
    assert state_response.json()["player"]["x"] == 0
    assert state_response.json()["player"]["y"] == 0


def test_mob_movement(client, auth_token,session):

    user = session.exec(select(User)).first()

    session.add(Mob(x=5, y=5, user_id=user.id, health=50))
    session.commit()

    for _ in range(3):
        client.post("/game/move", json={"direction": "right"}, headers={"Authorization": f"Bearer {auth_token}"})

    state_response = client.get("/game/state", headers={"Authorization": f"Bearer {auth_token}"})
    mobs = state_response.json()["mobs"]
    assert any(m["x"] != 5 or m["y"] != 5 for m in mobs)


def test_upgrade_system(client, auth_token, session):
    user = session.exec(select(User)).first()
    user.killed_mobs += 4
    session.commit()

    # Добавьте вызов apply_upgrades
    from app.routes.game import apply_upgrades
    apply_upgrades(user, session)

    response = client.get(
        "/game/upgrades",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    assert response.json()["bonus_attack"] > 0