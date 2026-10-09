from __future__ import annotations

import pytest

from campus.conversation_memory import PrincipleConversationMemory


def test_memory_keeps_only_the_recent_bounded_turns(tmp_path) -> None:
    memory = PrincipleConversationMemory(tmp_path / "memory.sqlite3", max_turns=3)

    for index in range(5):
        memory.append_turn(
            "session-a",
            "SIM-USER-001",
            user_message=f"question-{index}",
            assistant_message=f"answer-{index}",
        )

    assert memory.history("session-a", "SIM-USER-001") == [
        {"role": "user", "content": "question-2"},
        {"role": "assistant", "content": "answer-2"},
        {"role": "user", "content": "question-3"},
        {"role": "assistant", "content": "answer-3"},
        {"role": "user", "content": "question-4"},
        {"role": "assistant", "content": "answer-4"},
    ]


def test_memory_isolated_by_session_and_identity(tmp_path) -> None:
    memory = PrincipleConversationMemory(tmp_path / "memory.sqlite3")
    memory.append_turn(
        "session-a", "SIM-USER-001", user_message="mine", assistant_message="mine-answer"
    )
    memory.append_turn(
        "session-b", "SIM-USER-002", user_message="theirs", assistant_message="theirs-answer"
    )

    assert memory.history("session-b", "SIM-USER-002")[0]["content"] == "theirs"
    with pytest.raises(PermissionError):
        memory.history("session-a", "SIM-USER-002")
    with pytest.raises(PermissionError):
        memory.append_turn(
            "session-a", "SIM-USER-002", user_message="cross", assistant_message="write"
        )


def test_memory_clear_deletes_only_the_owned_session(tmp_path) -> None:
    memory = PrincipleConversationMemory(tmp_path / "memory.sqlite3")
    memory.append_turn(
        "session-a", "SIM-USER-001", user_message="mine", assistant_message="answer"
    )
    memory.append_turn(
        "session-b", "SIM-USER-002", user_message="theirs", assistant_message="answer"
    )

    with pytest.raises(PermissionError):
        memory.clear("session-a", "SIM-USER-002")
    assert memory.clear("session-a", "SIM-USER-001") is True
    assert memory.clear("session-a", "SIM-USER-001") is False
    assert memory.history("session-a", "SIM-USER-001") == []
    assert memory.history("session-b", "SIM-USER-002")[0]["content"] == "theirs"
