# tests/test_inventory.py
import pytest
from sqlmodel import Session, select, delete

from app.models import InventoryItem, MapTile, User, Mob


@pytest.fixture
def auth_token(client):
    # Регистрация и получение токена
    client.post("/auth/register", json={"username": "testuser", "password": "testpass"})
    response = client.post(
        "/auth/login",
        data={"username": "testuser", "password": "testpass"}
    )
    return response.json()["access_token"]


def test_get_empty_inventory(client, auth_token):
    response = client.get(
        "/inventory",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) == 0


def test_get_inventory_with_items(client, auth_token):
    # Добавляем предметы через генерацию карты
    client.post("/game/generate_map", headers={"Authorization": f"Bearer {auth_token}"})

    response = client.get(
        "/inventory",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) >= 1  # Стенолом добавляется при генерации


def test_use_wallbreaker_success(client, auth_token, session: Session):
    # Генерируем карту и находим игрока
    client.post("/game/generate_map", headers={"Authorization": f"Bearer {auth_token}"})
    user = session.exec(select(User)).first()

    # Проверяем начальное количество стенолома

    response = client.get("/inventory", headers={"Authorization": f"Bearer {auth_token}"})
    assert any(item["name"] == "Стенолом" for item in response.json()["items"])

    # Используем стенолом
    response = client.put(
        "/game/use-wallbreaker",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    assert "Уничтожено" in response.json()["message"]


def test_use_wallbreaker_no_item(client, auth_token, session: Session):
    # Удаляем все стеноломы
    session.exec(delete(InventoryItem).where(InventoryItem.name == "Стенолом"))
    session.commit()

    response = client.put(
        "/game/use-wallbreaker",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 400
    assert "У вас нет стенолома" in response.json()["detail"]


def test_wallbreaker_destroys_walls(client, auth_token, session: Session):
    user = session.exec(select(User)).first()
    session.add(InventoryItem(name="Стенолом", owner_id=user.id, quantity=1))
    session.add(MapTile(x=19, y=19, tile_type="exit", user_id=user.id))
    session.commit()
    user = session.exec(select(User)).first()

    walls = [
        (0, 1), (1, 0), (1, 1),
        (19, 18), (18, 19)
    ]
    for x, y in walls:
        session.add(MapTile(x=x, y=y, tile_type="wall", user_id=user.id))
    session.commit()

    response = client.put("/game/use-wallbreaker", headers={"Authorization": f"Bearer {auth_token}"})

    destroyed = 0
    for x, y in walls:
        tile = session.exec(select(MapTile).where(
            MapTile.x == x,
            MapTile.y == y,
            MapTile.user_id == user.id
        )).first()
        if tile and tile.tile_type == "floor":
            destroyed += 1

    assert destroyed >= 1


def test_wallbreaker_exit_not_found(client, auth_token, session: Session):
    # Получаем пользователя из БД
    user = session.exec(select(User)).first()

    # Добавляем стенолом перед удалением выхода
    session.add(InventoryItem(name="Стенолом", owner_id=user.id, quantity=1))

    # Удаляем выход
    session.exec(delete(MapTile).where(MapTile.tile_type == "exit"))
    session.commit()

    # Отправляем запрос
    response = client.put(
        "/game/use-wallbreaker",
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 400
    assert "Выход не найден" in response.json()["detail"]


def test_add_item_to_inventory(client, auth_token, session: Session):

    user = session.exec(select(User)).first()
    session.add(InventoryItem(name="Жажда", owner_id=user.id, quantity=1))
    session.commit()

    response = client.get(
        "/inventory",
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 200
    assert any(item["name"] == "Жажда" for item in response.json()["items"])