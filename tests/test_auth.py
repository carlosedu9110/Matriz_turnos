"""Pruebas del flujo de autenticación: login y acceso protegido."""


def test_login_success(client, sample_user):
    response = client.post("/auth/login", json={"username": "apere", "password": "Secret123!"})
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


def test_login_invalid_password(client, sample_user):
    response = client.post("/auth/login", json={"username": "apere", "password": "wrong"})
    assert response.status_code == 401


def test_login_unknown_user(client):
    response = client.post("/auth/login", json={"username": "nadie", "password": "x"})
    assert response.status_code == 401


def test_me_requires_token(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_with_valid_token(client, sample_user):
    login_response = client.post("/auth/login", json={"username": "apere", "password": "Secret123!"})
    token = login_response.json()["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "apere"
    assert body["email"] == "apere@example.com"
    assert any(rol["nombre"] == "Administrador" for rol in body["roles"])


def test_me_with_invalid_token(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401
