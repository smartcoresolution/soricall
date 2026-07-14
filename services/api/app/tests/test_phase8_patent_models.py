from sqlalchemy import inspect

from app.core.database import Base, engine


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_patent_call_flow_tables_are_created() -> None:
    tables = set(inspect(engine).get_table_names())

    assert {
        "call_sessions",
        "family_confirmations",
        "risk_decisions",
        "response_actions",
    }.issubset(tables)


def test_patent_call_flow_foreign_keys_are_declared() -> None:
    inspector = inspect(engine)

    decision_targets = {
        foreign_key["referred_table"]
        for foreign_key in inspector.get_foreign_keys("risk_decisions")
    }
    action_targets = {
        foreign_key["referred_table"]
        for foreign_key in inspector.get_foreign_keys("response_actions")
    }

    assert decision_targets == {"call_sessions", "voice_profiles"}
    assert action_targets == {"call_sessions", "risk_decisions"}
