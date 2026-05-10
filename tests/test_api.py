"""
Basic API tests executed in the CI Test stage.
Uses FastAPI's TestClient — no live server required.
"""
import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_returns_200():
    response = client.get("/health")
    assert response.status_code == 200


def test_health_response_shape():
    data = client.get("/health").json()
    assert "status" in data


def test_register_and_login():
    payload = {"username": "ci_test_user", "password": "ci_test_pass_123"}

    reg = client.post("/auth/register", json=payload)
    # 200 on first run; 400 if user already exists from a previous run — both are fine
    assert reg.status_code in (200, 400)

    login = client.post("/auth/login", json=payload)
    assert login.status_code == 200
    assert "token" in login.json()


def test_upload_requires_auth():
    response = client.post("/upload")
    assert response.status_code in (401, 422)


def test_list_uploads_requires_auth():
    response = client.get("/uploads")
    assert response.status_code in (401, 403, 422)
