def test_register(client):
    response = client.post(
        "/auth/register",
        json={"username": "testuser", "password": "testpass"}
    )
    assert response.status_code == 200
    assert response.json()["username"] == "testuser"

def test_register_duplicate(client):
    client.post("/auth/register", json={"username": "testuser", "password": "testpass"})
    response = client.post(
        "/auth/register",
        json={"username": "testuser", "password": "testpass"}
    )
    assert response.status_code == 400
    assert "Username already registered" in response.json()["detail"]

def test_login(client):
    client.post("/auth/register", json={"username": "testuser", "password": "testpass"})
    response = client.post(
        "/auth/login",
        data={"username": "testuser", "password": "testpass"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_invalid_credentials(client):
    response = client.post(
        "/auth/login",
        data={"username": "wronguser", "password": "wrongpass"}
    )
    assert response.status_code == 401