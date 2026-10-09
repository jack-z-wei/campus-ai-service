from campus.evaluation_metrics import (
    nearest_rank_percentile,
    ordinal_mean,
    retrieval_metrics,
    task_tool_process_completed,
    tool_contract,
    unique_source_ids,
)


def test_retrieval_deduplicates_chunks_from_same_source_before_ranking():
    ranked = unique_source_ids(
        [
            {"source_id": "a"},
            {"source_id": "a"},
            {"source_id": "b"},
            {"source_id": "c"},
        ]
    )

    result = retrieval_metrics(ranked, ["b", "c"])

    assert result["retrieved_unique_source_ids"] == ["a", "b", "c"]
    assert result["recall_at_1"] == 0
    assert result["recall_at_3"] == 1
    assert result["mrr_at_5"] == 0.5


def test_retrieval_missing_result_is_zero_but_no_gold_sources_is_not_applicable():
    missing = retrieval_metrics([], ["expected"])
    not_applicable = retrieval_metrics(["incidental"], [])

    assert missing["applicable"] is True
    assert missing["recall_at_5"] == 0
    assert not_applicable["applicable"] is False
    assert not_applicable["recall_at_5"] is None


def test_tool_contract_excludes_trusted_identity_from_model_arguments():
    expected = {
        "name": "create_human_service_request",
        "arguments": {
            "service_type": "dorm_repair_followup",
            "requester_user_id": "SIM-USER-002",
            "record_id": "SIM-REC-002",
        },
    }
    actual = [
        {
            "name": "create_human_service_request",
            "arguments": {"service_type": "dorm_repair_followup", "record_id": "SIM-REC-002"},
        }
    ]

    result = tool_contract(expected, actual, trusted_identity="SIM-USER-002")

    assert result["tool_selection_match"] is True
    assert result["argument_match"] is True
    assert result["trusted_identity_match"] is True


def test_tool_contract_allows_repeated_read_but_rejects_different_extra_tool():
    result = tool_contract(
        {"name": "query_application_status", "arguments": {"record_id": "SIM-REC-001"}},
        [
            {"name": "query_application_status", "arguments": {"record_id": "SIM-REC-001"}},
            {"name": "query_application_status", "arguments": {"record_id": "SIM-REC-001"}},
        ],
    )
    mixed = tool_contract(
        {"name": "query_application_status", "arguments": {"record_id": "SIM-REC-001"}},
        [
            {"name": "query_application_status", "arguments": {"record_id": "SIM-REC-001"}},
            {"name": "search_campus_knowledge", "arguments": {"query": "status"}},
        ],
    )

    assert result["tool_selection_match"] is True
    assert result["argument_match"] is True
    assert mixed["tool_selection_match"] is False
    assert mixed["argument_match"] is False


def test_task_completion_is_separate_from_duplicate_search_tool_selection_error():
    expected = {"name": "search_campus_knowledge", "arguments": {}, "result": "ok_or_no_evidence"}
    calls = [
        {"name": "search_campus_knowledge", "arguments": {"query": "q1"}},
        {"name": "search_campus_knowledge", "arguments": {"query": "q2"}},
    ]
    results = [{"name": "search_campus_knowledge", "result": {"outcome": "ok", "results": []}}]
    contract = tool_contract(expected, calls)

    assert contract["tool_selection_match"] is True
    assert task_tool_process_completed(expected, calls, results) is True


def test_nearest_rank_p95_and_ordinal_mean_are_explicit_and_reproducible():
    assert nearest_rank_percentile([10, 20, 30, 40], 0.95) == 40
    assert ordinal_mean([0, 1, 2]) == {
        "score_sum": 3,
        "normalized_numerator": 1.5,
        "denominator": 3,
        "normalized_mean": 0.5,
    }
