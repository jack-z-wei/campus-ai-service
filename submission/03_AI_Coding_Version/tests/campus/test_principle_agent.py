from __future__ import annotations

import json

import httpx

from campus.chunking import TextChunk
from campus.context_expansion import expand_top_hit_continuation
from campus.knowledge import CampusKnowledgeSearch
from campus.principle_agent import PrincipleAgent
from campus.principle_tools import ToolExecutionContext, ToolRegistry
from campus.retrieval import RetrievalHit
from campus.tools.status import CampusStatusTools


class _EmbeddingStub:
    def embed_query(self, _text: str) -> list[float]:
        return [1.0, 0.0]


def _search() -> CampusKnowledgeSearch:
    chunk = TextChunk(
        chunk_id="principle-test-chunk",
        source_id="academic_course_selection_2022",
        text="2022 年试行办法写明每学期一般以 15 至 35 学分为宜。",
        metadata={
            "title": "本科生选课办法",
            "url": "https://example.invalid/course",
            "published_on": "2022",
            "scope": "本科生",
            "index_policy": "current_homepage_snapshot",
        },
    )
    return CampusKnowledgeSearch([chunk], [[1.0, 0.0]], _EmbeddingStub())


def _completion(message: dict, request_number: int) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": f"completion-{request_number}",
            "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": 40 + request_number,
                "completion_tokens": 12,
                "total_tokens": 52 + request_number,
            },
        },
    )


def test_tool_schemas_hide_identity_and_fix_search_top_k() -> None:
    registry = ToolRegistry()
    definitions = {item["function"]["name"]: item for item in registry.definitions}
    status_schema = definitions["query_application_status"]["function"]["parameters"]
    search_schema = definitions["search_campus_knowledge"]["function"]["parameters"]

    assert set(status_schema["properties"]) == {"record_id", "service_type"}
    assert set(search_schema["properties"]) == {"query"}
    assert "top_k" not in search_schema["properties"]
    assert [item["function"]["name"] for item in registry.definitions_for(None)] == [
        "search_campus_knowledge"
    ]
    assert len(registry.definitions_for("SIM-USER-001")) == 3


def test_principle_agent_only_advertises_knowledge_search_without_demo_identity(tmp_path) -> None:
    requests: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return _completion(
            {"role": "assistant", "content": "请先完成演示身份配置。", "tool_calls": []}, 1
        )

    agent = PrincipleAgent(
        knowledge_search=_search(),
        status_tools=CampusStatusTools(tmp_path / "principle-no-identity.sqlite3"),
        api_key="test-only-key",
        base_url="https://model.example.invalid",
        model="deepseek-flash",
        prompt="Test prompt.",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    agent.run("帮我查 SIM-REC-001。", request_id="principle-no-identity")

    assert [item["function"]["name"] for item in requests[0]["tools"]] == [
        "search_campus_knowledge"
    ]


def test_truncated_top_hit_adds_only_the_nonoverlapping_adjacent_continuation() -> None:
    anchor = TextChunk(
        chunk_id="anchor",
        source_id="same-source",
        text="一二三四五审",
        metadata={"chunk_index": 0, "char_count": 500, "start_char": 0, "end_char": 6},
    )
    continuation = TextChunk(
        chunk_id="next",
        source_id="same-source",
        text="四五审核完成。",
        metadata={"chunk_index": 1, "char_count": 500, "start_char": 3, "end_char": 10},
    )

    expanded, records = expand_top_hit_continuation(
        [RetrievalHit(rank=1, score=0.9, chunk=anchor)], [anchor, continuation]
    )

    assert [item.chunk.text for item in expanded] == ["一二三四五审", "核完成。"]
    assert expanded[1].expanded_from_chunk_id == "anchor"
    assert records[0]["overlap_chars_removed"] == 3


def test_registry_validates_identity_from_context_and_rejects_unknown_tool(tmp_path) -> None:
    registry = ToolRegistry()
    status = CampusStatusTools(tmp_path / "principle.sqlite3")
    context = ToolExecutionContext(_search(), status, "SIM-USER-001", "request-1")

    forbidden = registry.execute(
        "query_application_status",
        json.dumps({"record_id": "SIM-REC-002", "service_type": "dorm_repair"}),
        context,
    )
    invalid = registry.execute(
        "query_application_status",
        json.dumps({"record_id": "SIM-REC-001' OR 1=1 --", "service_type": "aid_application"}),
        context,
    )
    unknown = registry.execute("not_registered", "{}", context)
    owned_status = registry.execute(
        "query_application_status",
        json.dumps({"record_id": "SIM-REC-001"}),
        ToolExecutionContext(_search(), status, "SIM-USER-001", "request-1"),
    )

    assert forbidden["outcome"] == "forbidden"
    assert invalid["outcome"] == "invalid_arguments"
    assert unknown["outcome"] == "unknown_tool"
    assert owned_status["outcome"] == "found"
    assert owned_status["service_type"] == "aid_application"
    assert "SIM-USER-002" not in json.dumps(forbidden, ensure_ascii=False)


def test_principle_agent_runs_explicit_search_then_function_call_then_answer(tmp_path) -> None:
    requests: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        if len(requests) == 1:
            return _completion(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "status-call-1",
                            "type": "function",
                            "function": {
                                "name": "query_application_status",
                                "arguments": json.dumps(
                                    {
                                        "record_id": "SIM-REC-001",
                                        "service_type": "aid_application",
                                    }
                                ),
                            },
                        }
                    ],
                },
                1,
            )
        return _completion(
            {"role": "assistant", "content": "模拟记录显示材料审核中。", "tool_calls": []}, 2
        )

    status = CampusStatusTools(tmp_path / "principle-agent.sqlite3")
    agent = PrincipleAgent(
        knowledge_search=_search(),
        status_tools=status,
        api_key="test-only-key",
        base_url="https://model.example.invalid",
        model="deepseek-flash",
        prompt="使用给定证据并按需调用工具。",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    result = agent.run(
        "请查询我的模拟助学申请 SIM-REC-001。",
        authenticated_user_id="SIM-USER-001",
        request_id="principle-test-request",
    )

    assert result["status"] == "completed"
    assert result["answer"] == "模拟记录显示材料审核中。"
    assert result["retrieval"]["backend"] == "numpy"
    assert result["retrieval"]["evidence"][0]["source_id"] == "academic_course_selection_2022"
    assert result["tool_calls"][0]["result"]["status"] == "材料审核中"
    assert [message["role"] for message in requests[1]["messages"][-2:]] == ["assistant", "tool"]
    assert result["model_requests"][0]["usage"]["input_tokens"] == 41


def test_principle_agent_includes_prior_completed_turns_before_current_question(tmp_path) -> None:
    captured: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.extend(json.loads(request.content)["messages"])
        return _completion(
            {"role": "assistant", "content": "按前文继续处理。", "tool_calls": []}, 1
        )

    agent = PrincipleAgent(
        knowledge_search=_search(),
        status_tools=CampusStatusTools(tmp_path / "principle-memory-agent.sqlite3"),
        api_key="test-only-key",
        base_url="https://model.example.invalid",
        model="deepseek-flash",
        prompt="Test prompt.",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    result = agent.run(
        "那帮我转人工。",
        request_id="principle-memory-request",
        conversation_history=[
            {"role": "user", "content": "我的宿舍报修单是 SIM-REC-002。"},
            {"role": "assistant", "content": "我查到模拟维修记录。"},
        ],
    )

    assert result["status"] == "completed"
    assert result["memory"]["prior_turn_count"] == 1
    assert [message["role"] for message in captured[-3:]] == ["user", "assistant", "user"]
    assert captured[-3]["content"] == "我的宿舍报修单是 SIM-REC-002。"
    assert captured[-2]["content"] == "我查到模拟维修记录。"
    assert captured[-1]["content"] == "那帮我转人工。"


def test_principle_agent_rejects_unbounded_or_malformed_history(tmp_path) -> None:
    agent = PrincipleAgent(
        knowledge_search=_search(),
        status_tools=CampusStatusTools(tmp_path / "principle-invalid-memory.sqlite3"),
        api_key="test-only-key",
        base_url="https://model.example.invalid",
        model="deepseek-flash",
        prompt="Test prompt.",
        client=httpx.Client(transport=httpx.MockTransport(lambda _request: _completion({}, 1))),
    )

    for history in (
        [{"role": "assistant", "content": "orphaned"}],
        [
            message
            for turn in range(5)
            for message in (
                {"role": "user", "content": f"q-{turn}"},
                {"role": "assistant", "content": f"a-{turn}"},
            )
        ],
    ):
        try:
            agent.run("current", request_id="invalid-history", conversation_history=history)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected malformed or oversized history to be rejected.")


def test_principle_agent_stops_when_model_exceeds_per_response_call_limit(tmp_path) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        calls = [
            {
                "id": f"call-{index}",
                "type": "function",
                "function": {"name": "query_application_status", "arguments": "{}"},
            }
            for index in range(3)
        ]
        return _completion(
            {"role": "assistant", "content": None, "tool_calls": calls},
            1,
        )

    agent = PrincipleAgent(
        knowledge_search=_search(),
        status_tools=CampusStatusTools(tmp_path / "principle-limit.sqlite3"),
        api_key="test-only-key",
        base_url="https://model.example.invalid",
        model="deepseek-flash",
        prompt="Test prompt.",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    result = agent.run("查看状态", request_id="principle-limit-request")

    assert result["status"] == "tool_call_limit_reached"
    assert result["tool_calls"] == []
    assert result["total_tool_calls"] == 0
