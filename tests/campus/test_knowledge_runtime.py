from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import campus.runtime as runtime


def test_chroma_search_initializes_once_on_parallel_first_access(monkeypatch) -> None:
    monkeypatch.setattr(runtime, "_CAMPUS_KNOWLEDGE_SEARCH", None)
    build_count = 0
    count_lock = threading.Lock()
    start = threading.Barrier(8)
    sentinel = object()

    def build_search():
        nonlocal build_count
        with count_lock:
            build_count += 1
        time.sleep(0.02)
        return sentinel

    def get_search():
        start.wait(timeout=2)
        return runtime.get_campus_knowledge_search()

    monkeypatch.setattr(runtime, "_build_campus_knowledge_search", build_search)
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _: get_search(), range(8)))

    assert build_count == 1
    assert all(result is sentinel for result in results)
