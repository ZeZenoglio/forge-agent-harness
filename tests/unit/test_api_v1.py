import time
from unittest.mock import patch

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.models import Base, User
from backend.db.session import get_db
from backend.main import app
from backend.services.auth_service import AUTHENTIK_SECRET

# Setup test DB with StaticPool so all connections share the same memory database
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(
    test_engine,
    tables=[
        Base.metadata.tables["users"],
        Base.metadata.tables["sessions"],
        Base.metadata.tables["conversations"],
        Base.metadata.tables["messages"],
        Base.metadata.tables["agent_runs"],
        Base.metadata.tables["agent_events"],
        Base.metadata.tables["tool_calls"],
        Base.metadata.tables["artifacts"],
        Base.metadata.tables["documents"],
    ],
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_docs_and_redoc_endpoints() -> None:
    res_docs = client.get("/docs")
    assert res_docs.status_code == 200

    res_redoc = client.get("/redoc")
    assert res_redoc.status_code == 200


def test_health_endpoints() -> None:
    res_root = client.get("/health")
    assert res_root.status_code == 200
    assert res_root.json()["status"] == "ok"
    assert res_root.json()["data"]["status"] == "ok"

    res_v1 = client.get("/api/v1/health")
    assert res_v1.status_code == 200
    assert res_v1.json()["data"]["status"] == "ok"


def test_rfc7807_problem_details_on_404() -> None:
    res = client.get("/api/v1/conversations/non-existent-id")
    assert res.status_code == 404
    assert res.headers["content-type"].startswith("application/problem+json")
    body = res.json()
    assert body["status"] == 404
    assert body["title"] == "Not Found"
    assert "detail" in body
    assert body["instance"] == "/api/v1/conversations/non-existent-id"


def test_tools_endpoints() -> None:
    res = client.get("/api/v1/tools")
    assert res.status_code == 200
    tools = res.json()["data"]
    assert any(t["name"] == "web_search" for t in tools)
    assert any(t["name"] == "extract_structured" for t in tools)
    assert any(t["name"] == "research_topic" for t in tools)

    res_tool = client.get("/api/v1/tools/web_search")
    assert res_tool.status_code == 200
    assert res_tool.json()["data"]["name"] == "web_search"


def test_conversations_and_messages_endpoints() -> None:
    # Create conversation
    create_res = client.post("/api/v1/conversations", json={"title": "Test Chat"})
    assert create_res.status_code == 201
    conv_data = create_res.json()["data"]
    conv_id = conv_data["id"]
    assert conv_data["title"] == "Test Chat"

    # List conversations
    list_res = client.get("/api/v1/conversations")
    assert list_res.status_code == 200
    assert any(c["id"] == conv_id for c in list_res.json()["data"])

    # Add message
    msg_res = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"role": "user", "content": "Hello world!"},
    )
    assert msg_res.status_code == 201
    assert msg_res.json()["data"]["content"] == "Hello world!"

    # Get conversation with messages
    get_conv = client.get(f"/api/v1/conversations/{conv_id}")
    assert get_conv.status_code == 200
    assert len(get_conv.json()["data"]["messages"]) == 1
    assert get_conv.json()["data"]["messages"][0]["content"] == "Hello world!"

    # Delete conversation
    del_res = client.delete(f"/api/v1/conversations/{conv_id}")
    assert del_res.status_code == 200
    assert del_res.json()["data"]["deleted"] is True


def test_agent_run_and_cancel_endpoints() -> None:
    with patch("backend.routes.agent.agent_task"):
        res = client.post("/api/v1/agent/run", json={"task": "Inspect code"})
        assert res.status_code == 200
        session_id = res.json()["data"]["session_id"]
        assert session_id

        # Test cancel
        cancel_res = client.post(f"/api/v1/agent/cancel/{session_id}")
        assert cancel_res.status_code == 200
        assert cancel_res.json()["data"]["cancelled"] is True


def test_authentik_jwt_validation_and_user_sync() -> None:
    # 1. Valid token syncs user
    payload = {
        "sub": "auth-user-123",
        "email": "user@example.com",
        "name": "Authentik User",
        "provider": "authentik",
        "exp": int(time.time()) + 3600,
    }
    token = jwt.encode(payload, AUTHENTIK_SECRET, algorithm="HS256")

    verify_res = client.post("/api/v1/auth/verify", json={"token": token})
    assert verify_res.status_code == 200
    assert verify_res.json()["data"]["email"] == "user@example.com"

    # User profile should exist in DB
    db = TestingSessionLocal()
    u = db.query(User).filter_by(email="user@example.com").first()
    assert u is not None
    assert u.name == "Authentik User"
    db.close()

    # 2. Expired token raises 401
    expired_payload = {
        "sub": "auth-user-123",
        "email": "user@example.com",
        "exp": int(time.time()) - 3600,
    }
    expired_token = jwt.encode(expired_payload, AUTHENTIK_SECRET, algorithm="HS256")

    bad_res = client.post("/api/v1/auth/verify", json={"token": expired_token})
    assert bad_res.status_code == 401
    assert bad_res.headers["content-type"].startswith("application/problem+json")
    assert "expired" in bad_res.json()["detail"].lower()


def test_social_login_account_merging() -> None:
    # User created first with email/password
    db = TestingSessionLocal()
    existing = User(
        id="local-user-456",
        email="social@company.com",
        name="Local Person",
        provider="authentik",
    )
    db.add(existing)
    db.commit()
    db.close()

    # Social login token arrives with GitHub as provider for same email
    github_payload = {
        "sub": "github-oauth2|998877",
        "email": "social@company.com",
        "name": "GitHub Person",
        "provider": "github",
        "avatar_url": "https://avatars.githubusercontent.com/u/998877",
        "exp": int(time.time()) + 3600,
    }
    gh_token = jwt.encode(github_payload, AUTHENTIK_SECRET, algorithm="HS256")

    res = client.post("/api/v1/auth/verify", json={"token": gh_token})
    assert res.status_code == 200

    # Verify existing account was merged with GitHub provider & updated profile
    db = TestingSessionLocal()
    merged = db.query(User).filter_by(email="social@company.com").first()
    assert merged is not None
    assert merged.provider == "github"
    assert merged.name == "GitHub Person"
    assert merged.avatar_url == "https://avatars.githubusercontent.com/u/998877"
    db.close()
