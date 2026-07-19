from sqlalchemy import inspect

from app.core.database import Base, engine
from app.models import ResponseAction, RiskDecision


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
    decision_targets = {
        foreign_key.column.table.name
        for foreign_key in RiskDecision.__table__.foreign_keys
    }
    action_targets = {
        foreign_key.column.table.name
        for foreign_key in ResponseAction.__table__.foreign_keys
    }

    assert decision_targets == {"call_sessions", "voice_profiles"}
    assert action_targets == {"call_sessions", "risk_decisions"}
