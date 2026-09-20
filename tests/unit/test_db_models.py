import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session as DBSession

from backend.db.models import (
    AgentEvent,
    AgentRun,
    Artifact,
    Base,
    Conversation,
    Document,
    Message,
    Session,
    ToolCall,
    User,
)


def test_models_creation_and_relationships() -> None:
    # Use SQLite in-memory for unit testing (excluding vector hnsw index on non-pg)
    engine = create_engine("sqlite:///:memory:")
    # Create tables (ignoring pgvector specific type for sqlite test by creating base tables)
    # Using Base.metadata.create_all with tables except embedding
    tables = [
        User.__table__,
        Session.__table__,
        Conversation.__table__,
        Message.__table__,
        AgentRun.__table__,
        AgentEvent.__table__,
        ToolCall.__table__,
        Artifact.__table__,
        Document.__table__,
    ]
    Base.metadata.create_all(engine, tables=tables)

    with DBSession(engine) as session:
        # Create user
        user = User(
            id=str(uuid.uuid4()),
            email="test@example.com",
            name="Test User",
            provider="authentik",
        )
        session.add(user)
        session.commit()

        # Create session
        user_session = Session(
            id=str(uuid.uuid4()),
            user_id=user.id,
            token="jwt-token-123",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        session.add(user_session)

        # Create conversation
        conv = Conversation(
            id=str(uuid.uuid4()),
            user_id=user.id,
            title="Test Conversation",
        )
        session.add(conv)
        session.commit()

        # Create message
        msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conv.id,
            role="user",
            content="Hello agent",
        )
        session.add(msg)

        # Create agent run
        run = AgentRun(
            id=str(uuid.uuid4()),
            conversation_id=conv.id,
            status="completed",
            model="default-agent",
        )
        session.add(run)
        session.commit()

        # Create event with monotonic seq
        event = AgentEvent(
            id=str(uuid.uuid4()),
            run_id=run.id,
            seq=1,
            event_type="plan",
            payload={"steps": ["Step 1", "Step 2"]},
        )
        session.add(event)

        # Create tool call
        tool_call = ToolCall(
            id=str(uuid.uuid4()),
            run_id=run.id,
            tool_name="web_search",
            input_payload='{"query": "antigravity"}',
            output_payload='[{"title": "Antigravity", "url": "https://example.com"}]',
            status="success",
        )
        session.add(tool_call)

        # Create artifact
        artifact = Artifact(
            id=str(uuid.uuid4()),
            conversation_id=conv.id,
            name="report.pdf",
            mime_type="application/pdf",
            content_bytes=b"%PDF-1.4 test bytes",
        )
        session.add(artifact)
        session.commit()

        # Query & verify relationships
        saved_user = session.query(User).filter_by(email="test@example.com").first()
        assert saved_user is not None
        assert len(saved_user.conversations) == 1
        assert saved_user.conversations[0].title == "Test Conversation"
        assert len(saved_user.conversations[0].messages) == 1
        assert saved_user.conversations[0].messages[0].content == "Hello agent"
        assert len(saved_user.conversations[0].agent_runs) == 1
        assert len(saved_user.conversations[0].agent_runs[0].events) == 1
        assert saved_user.conversations[0].agent_runs[0].events[0].seq == 1
        assert len(saved_user.conversations[0].agent_runs[0].tool_calls) == 1
        assert (
            saved_user.conversations[0].agent_runs[0].tool_calls[0].tool_name
            == "web_search"
        )
        assert len(saved_user.conversations[0].artifacts) == 1
        assert saved_user.conversations[0].artifacts[0].name == "report.pdf"
