from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.routers.auth import router as auth_router
from app.security import (
    authenticate_user,
    create_access_token,
    require_roles,
    verify_access_token,
)


def test_authenticate_user_roles() -> None:
    assert authenticate_user("admin", "admin123") == "operator"
    assert authenticate_user("operator", "operator123") == "operator"
    assert authenticate_user("viewer", "viewer123") == "viewer"
    assert authenticate_user("viewer", "wrong") is None


def test_create_and_verify_access_token_round_trip() -> None:
    token = create_access_token("viewer", "viewer")
    payload = verify_access_token(token)
    assert payload["sub"] == "viewer"
    assert payload["role"] == "viewer"


def test_login_endpoint_returns_role_and_token() -> None:
    app = FastAPI()
    app.include_router(auth_router)
    client = TestClient(app)

    response = client.post("/auth/login", json={"username": "viewer", "password": "viewer123"})
    assert response.status_code == 200

    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["role"] == "viewer"
    assert isinstance(body["access_token"], str)


def test_require_roles_allows_operator_denies_viewer() -> None:
    app = FastAPI()

    @app.get("/operator-only")
    def operator_only(_: str = Depends(require_roles("operator"))):
        return {"ok": True}

    client = TestClient(app)

    viewer_token = create_access_token("viewer", "viewer")
    viewer_response = client.get("/operator-only", headers={"Authorization": f"Bearer {viewer_token}"})
    assert viewer_response.status_code == 403

    operator_token = create_access_token("operator", "operator")
    operator_response = client.get("/operator-only", headers={"Authorization": f"Bearer {operator_token}"})
    assert operator_response.status_code == 200
    assert operator_response.json() == {"ok": True}
