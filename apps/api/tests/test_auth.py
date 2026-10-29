from collections.abc import Callable
from typing import Any, cast

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.models.user import Users

LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
ME = "/api/v1/auth/me"


def login(
    client: TestClient, username: str = "alice", password: str = "password123"
) -> dict[str, Any]:
    response = client.post(LOGIN, json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def test_login_and_me(client: TestClient, create_user: Callable[..., Users]) -> None:
    create_user()
    data = login(client)
    assert data["username"] == "alice"
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["expires_in"] > 0

    me = client.get(ME, headers={"Authorization": f"Bearer {data['access_token']}"})
    assert me.status_code == 200
    assert me.json()["username"] == "alice"


def test_login_wrong_password(client: TestClient, create_user: Callable[..., Users]) -> None:
    create_user()
    response = client.post(LOGIN, json={"username": "alice", "password": "wrong-password"})
    assert response.status_code == 401
    assert response.json()["detail"] == "用户名或密码错误"


def test_login_unknown_user(client: TestClient) -> None:
    response = client.post(LOGIN, json={"username": "nobody", "password": "password123"})
    assert response.status_code == 401


def test_disabled_user_cannot_login(client: TestClient, create_user: Callable[..., Users]) -> None:
    create_user(status=False)
    response = client.post(LOGIN, json={"username": "alice", "password": "password123"})
    assert response.status_code == 403
    assert response.json()["detail"] == "账号已被禁用"


def test_refresh_rotates_tokens(client: TestClient, create_user: Callable[..., Users]) -> None:
    create_user()
    first = login(client)
    response = client.post(REFRESH, json={"refresh_token": first["refresh_token"]})
    assert response.status_code == 200
    second = response.json()
    assert second["access_token"] != first["access_token"]

    me = client.get(ME, headers={"Authorization": f"Bearer {second['access_token']}"})
    assert me.status_code == 200


def test_access_and_refresh_tokens_are_not_interchangeable(
    client: TestClient, create_user: Callable[..., Users]
) -> None:
    create_user()
    data = login(client)

    as_refresh = client.post(REFRESH, json={"refresh_token": data["access_token"]})
    assert as_refresh.status_code == 401

    as_access = client.get(ME, headers={"Authorization": f"Bearer {data['refresh_token']}"})
    assert as_access.status_code == 401


def test_me_requires_token(client: TestClient) -> None:
    assert client.get(ME).status_code == 401
    assert client.get(ME, headers={"Authorization": "Bearer nonsense"}).status_code == 401


def test_register_endpoint_does_not_exist(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "newuser", "password": "password123"},
    )
    assert response.status_code == 404


def test_jwks_shape(client: TestClient) -> None:
    response = client.get("/.well-known/jwks.json")
    assert response.status_code == 200
    data = response.json()
    assert len(data["keys"]) == 1
    key = data["keys"][0]
    assert key["kty"] == "RSA"
    assert key["alg"] == "RS256"
    assert key["use"] == "sig"
    assert key["kid"]
    assert key["n"]
    assert key["e"]


def test_refresh_unknown_user(client: TestClient, create_user: Callable[..., Users]) -> None:
    user = create_user()
    data = login(client)
    with cast(FastAPI, client.app).state.session_factory() as session:
        stored = session.get(Users, user.user_id)
        assert stored is not None
        session.delete(stored)
        session.commit()

    response = client.post(REFRESH, json={"refresh_token": data["refresh_token"]})
    assert response.status_code == 401


def test_access_token_of_deleted_user(
    client: TestClient, create_user: Callable[..., Users]
) -> None:
    user = create_user()
    data = login(client)
    with cast(FastAPI, client.app).state.session_factory() as session:
        stored = session.get(Users, user.user_id)
        assert stored is not None
        session.delete(stored)
        session.commit()

    response = client.get(ME, headers={"Authorization": f"Bearer {data['access_token']}"})
    assert response.status_code == 401


def test_access_token_of_disabled_user(
    client: TestClient, create_user: Callable[..., Users]
) -> None:
    user = create_user()
    data = login(client)
    with cast(FastAPI, client.app).state.session_factory() as session:
        stored = session.get(Users, user.user_id)
        assert stored is not None
        stored.status = False
        session.commit()

    response = client.get(ME, headers={"Authorization": f"Bearer {data['access_token']}"})
    assert response.status_code == 401
