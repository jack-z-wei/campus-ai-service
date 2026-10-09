"""Assemble the six course handoff folders on the Windows project workspace."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "submission"
IGNORE = shutil.ignore_patterns(
    "__pycache__", "*.pyc", ".pytest_cache", ".ruff_cache", ".mypy_cache", ".venv"
)
ROUTE_RUNS = {
    "02_Python_Version": (
        ("baseline-principles-v1-20261006", "baseline-optimized-principles-v1-20261006"),
    ),
    "03_AI_Coding_Version": (
        ("baseline-engineering-v1-20261006", "baseline-optimized-engineering-v1-20261006"),
    ),
}
REQUIRED_DIRS = (
    "01_Coze_Version",
    "02_Python_Version",
    "03_AI_Coding_Version",
    "04_Evaluation",
    "05_Final_Report",
    "06_Demo",
)
SECRET_PATTERN = re.compile(r"(?i)\bsk-[a-z0-9]{24,}\b")


def copy_file(source: str, destination: str | Path | None = None) -> None:
    src = ROOT / source
    if not src.is_file():
        raise FileNotFoundError(src)
    target = OUT / (destination or Path(source))
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, target)


def copy_dir(source: str, destination: str | Path | None = None) -> None:
    src = ROOT / source
    if not src.is_dir():
        raise FileNotFoundError(src)
    target = OUT / (destination or Path(source))
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, target, dirs_exist_ok=True, ignore=IGNORE)


def coze_summary() -> dict[str, object]:
    path = ROOT / "coze" / "package_manifest.json"
    if not path.is_file():
        raise FileNotFoundError(f"Coze execution manifest is required: {path}")
    summary = json.loads(path.read_text(encoding="utf-8"))
    required = (
        "coze_acceptance_suite_executed",
        "coze_acceptance_case_count",
        "coze_acceptance_assistant_turn_count",
        "coze_course_deliverables_met",
    )
    missing = [key for key in required if key not in summary]
    if missing:
        raise ValueError(f"Coze execution manifest is missing fields: {missing}")
    return summary


def coze_manifest_fields() -> dict[str, object]:
    summary = coze_summary()
    return {
        "coze_platform_tested": bool(summary["coze_acceptance_suite_executed"]),
        "coze_partial_preview_recorded": bool(summary.get("coze_preview_recorded", False)),
        "coze_acceptance_case_count": int(summary["coze_acceptance_case_count"]),
        "coze_acceptance_assistant_turn_count": int(summary["coze_acceptance_assistant_turn_count"]),
        "coze_course_deliverables_met": bool(summary["coze_course_deliverables_met"]),
        "coze_course_acceptance_basis": summary.get("coze_course_acceptance_basis", ""),
        "coze_partial_case_count": int(summary.get("coze_partial_case_count", 0)),
        "coze_nonexecuted_frozen_case_count": int(summary.get("coze_nonexecuted_frozen_case_count", 0)),
        "coze_supplemental_retest_count": int(summary.get("coze_supplemental_retest_count", 0)),
        "coze_supplemental_retest_pass_count": int(summary.get("coze_supplemental_retest_pass_count", 0)),
        "coze_supplemental_retest_partial_count": int(summary.get("coze_supplemental_retest_partial_count", 0)),
        "coze_prompt_revision_date": summary.get("coze_prompt_revision_date", ""),
        "coze_prompt_platform_roundtrip_verified": bool(summary.get("coze_prompt_platform_roundtrip_verified", False)),
        "coze_teacher_acceptance_claimed": bool(summary.get("coze_teacher_acceptance_claimed", False)),
        "coze_billing_status": summary.get("billing_status", "unknown"),
    }


def rating_evidence_fields() -> dict[str, object]:
    """Summarize the saved rubric scores and their supporting traces."""
    path = ROOT / "reports" / "评分表_V1_V2.csv"
    if not path.is_file():
        raise FileNotFoundError(f"Rubric score evidence is required: {path}")
    totals: dict[str, int] = {}
    counts: dict[str, int] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            version = row["prompt_version"]
            if row.get("scorer") != "Codex":
                raise ValueError(f"Missing score source in {path.name}: {row.get('scorer')!r}.")
            score = sum(
                int(row[field])
                for field in ("correctness_0_2", "faithfulness_0_2", "citation_accuracy_0_2")
            )
            if not 0 <= score <= 6:
                raise ValueError(f"Invalid rubric row score in {path.name}.")
            totals[version] = totals.get(version, 0) + score
            counts[version] = counts.get(version, 0) + 1
    if counts != {"V1": 5, "V2": 5}:
        raise ValueError(f"Expected 5 saved rubric rows per version; found {counts}.")
    return {
        "scores_present": True,
        "score_source": "Codex",
        "score_method": "Fixed rubric applied to saved answers and retrieval traces",
        "score_case_count": sum(counts.values()),
        "score_case_count_by_version": counts,
        "score_by_version": {version: f"{totals[version]}/30" for version in sorted(totals)},
    }


def copy_route_runs(package_dir: str) -> None:
    dest_root = OUT / package_dir / "runs"
    for run_id in ("campus-index-20261006-173801", "retrieval-policy-20261006-173948"):
        copy_dir(f"runs/{run_id}", Path(package_dir) / "runs" / run_id)
    for parent_id in ROUTE_RUNS[package_dir][0]:
        parent_rel = f"runs/{parent_id}"
        copy_dir(parent_rel, Path(package_dir) / parent_rel)
        index_path = ROOT / parent_rel / "per_case.jsonl"
        for line in index_path.read_text(encoding="utf-8").splitlines():
            item = json.loads(line)
            child_id = item["run_id"]
            child = ROOT / "runs" / child_id
            if not child.is_dir():
                raise FileNotFoundError(child)
            copy_dir(f"runs/{child_id}", Path(package_dir) / "runs" / child_id)
    if not dest_root.is_dir():
        raise RuntimeError(f"Route evidence was not copied: {dest_root}")


def copy_evaluation_runs() -> None:
    """Copy stable evaluation artifacts, omitting mutable local UI preview state."""
    source_root = ROOT / "runs"
    target_root = OUT / "04_Evaluation" / "runs"
    target_root.mkdir(parents=True, exist_ok=True)
    for run_dir in source_root.iterdir():
        if not run_dir.is_dir():
            continue
        if run_dir.name.startswith(("ui-preview-", "backend-preview-")):
            # A preview can remain live while packaging. Keep its immutable
            # manifest and UI test evidence, never copy mutable SQLite/log files.
            static_names = ("manifest.json", "live-ui-app-test.json", "live_ui_app_test.py")
            for name in static_names:
                source = run_dir / name
                if source.is_file():
                    target = target_root / run_dir.name / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
            continue
        copy_dir(f"runs/{run_dir.name}", Path("04_Evaluation/runs") / run_dir.name)


def refresh_manifest() -> None:
    """Re-scan an already assembled package without changing its payload files."""
    if sys.platform != "win32":
        raise SystemExit("Run this packaging script with the Windows project .venv.")
    if not OUT.is_dir() or not (OUT / "package_manifest.json").is_file():
        raise SystemExit("A completed submission/ package with package_manifest.json is required.")
    missing = [name for name in REQUIRED_DIRS if not (OUT / name).is_dir()]
    if missing:
        raise RuntimeError(f"Missing required submission directories: {missing}")
    forbidden = [
        path
        for path in OUT.rglob("*")
        if path.is_dir()
        and path.name in {".venv", ".git", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
        or (path.is_file() and path.name == ".env")
    ]
    if forbidden:
        raise RuntimeError("Forbidden runtime/secret paths were found in submission.")
    suspicious_files = []
    file_rows = []
    for path in sorted(p for p in OUT.rglob("*") if p.is_file() and p.name != "package_manifest.json"):
        raw = path.read_bytes()
        if SECRET_PATTERN.search(raw.decode("utf-8", errors="ignore")) and path.name != ".env.example":
            suspicious_files.append(str(path.relative_to(OUT)))
        file_rows.append(
            {
                "path": str(path.relative_to(OUT)).replace("\\", "/"),
                "size_bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    if suspicious_files:
        raise RuntimeError("Possible credential pattern found in package files; values were not printed.")

    manifest = {
        "created_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
        "status": "technical_package_complete_scope_limited",
        "platform": "win32",
        "directory_count": len(REQUIRED_DIRS),
        "directories": list(REQUIRED_DIRS),
        "file_count": len(file_rows),
        "contains_dotenv": False,
        "contains_virtual_environment": False,
        **coze_manifest_fields(),
        **rating_evidence_fields(),
        "technical_artifact_package_complete": True,
        "user_excluded_scope_items": ["personal signature", "course live demonstration", "teacher permission"],
        "coze_publication_claimed": False,
        "teacher_permission_claimed": False,
        "distinct_retrieval_failure_count_confirmed": 3,
        "distinct_retrieval_failure_threshold": 3,
        "unresolved_retrieval_failure_count": 1,
        "files": file_rows,
    }
    (OUT / "package_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": manifest["status"], "directories": len(REQUIRED_DIRS), "files": len(file_rows)}, ensure_ascii=True))


def write_route_readmes() -> None:
    python_readme = """# Python 原理版源码快照

本目录只把 Python 显式 RAG / ToolRegistry CLI 作为演示入口；不依赖 LangGraph Agent 执行。共用的配置/schema 模块随源码一并复制，工程版另在 `../03_AI_Coding_Version/`。

## Windows PowerShell

```powershell
Set-Location <本目录的完整 Windows 路径>
uv sync --frozen
# 先用本机 Ollama 做不收费的检索验证：
.\\.venv\\Scripts\\python.exe scripts\\run_campus_principles_windows.py `
  --question "长安大学本科生每学期修读多少学分比较合适？" --retrieval-only
# 真实 DeepSeek 聊天需在本目录本机 .env 配置自己的 Key；不要提交或分享该文件。
```

运行还需要本机 Ollama `bge-m3:latest`。固定来源、冻结用例、向量索引和本路线独立 traces 在本目录；工程版独立 traces 在兄弟工程包和 `../04_Evaluation/`。不得用旧 trace 冒充本次新运行。
"""
    engineering_readme = """# 长安大学校园智能客服助手：工程版

本目录是校园客服的 Windows 工程运行包，浏览器界面固定连接 `campus-customer-service`。提供校园资料问答、合成业务状态查询和本地模拟服务登记。

## Windows PowerShell

```powershell
Set-Location <本目录的完整 Windows 路径>
uv sync --frozen
# 本地演示：API 与页面使用独立 SQLite，并打开默认浏览器
.\\.venv\\Scripts\\python.exe scripts\\launch_local_demo_windows.py
# 或手动分别启动 API 和 UI
.\\.venv\\Scripts\\python.exe src\\run_service.py
.\\.venv\\Scripts\\streamlit.exe run src\\streamlit_app.py
# 测试
.\\.venv\\Scripts\\python.exe -m pytest tests\\campus tests\\app -q
```

模型服务在运行者本机配置；不要复制提交开发目录中的 `.env`。知识回答显示检索来源；事项状态和服务登记仅操作合成记录，不连接学校业务系统。请勿输入真实个人信息。

## 工程来源

校园 Agent、检索管线、工具合同、合成数据、课程 UI 和评测材料按本项目需求改造。服务、消息协议及部分基础模块复用了公开 MIT 工程项目；固定提交和文件级复用说明见 `UPSTREAM.md`，原始 `LICENSE` 保留。教师复用许可状态以课程沟通结果为准。
"""
    (OUT / "02_Python_Version" / "README.md").write_text(python_readme, encoding="utf-8")
    (OUT / "03_AI_Coding_Version" / "README.md").write_text(
        engineering_readme, encoding="utf-8"
    )


def assemble() -> None:
    if sys.platform != "win32":
        raise SystemExit("Run this packaging script with the Windows project .venv.")
    if OUT.exists():
        existing = {path.name for path in OUT.iterdir()}
        unexpected = existing - set(REQUIRED_DIRS)
        if unexpected or (OUT / "package_manifest.json").exists():
            raise SystemExit(
                "submission/ contains files outside an incomplete package build; refusing to overwrite."
            )
    for obsolete_name in ("人工评分表_V1_V2.csv", "AI辅助评分表_V1_V2.csv", "人工评分说明.md"):
        (OUT / "04_Evaluation" / "reports" / obsolete_name).unlink(missing_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    for name in REQUIRED_DIRS:
        (OUT / name).mkdir(exist_ok=True)

    # 01: Coze configuration, real platform evidence, and declared limits.
    copy_dir("coze", "01_Coze_Version/coze")
    copy_file("reports/Coze_Python_Engineering_Mapping.md", "01_Coze_Version/module_mapping.md")
    coze_result = coze_summary()
    coze_screenshots = OUT / "01_Coze_Version" / "coze" / "screenshots"
    coze_screenshots.mkdir(exist_ok=True)
    copied_coze_images = sorted(path.name for path in coze_screenshots.glob("*.png"))
    if copied_coze_images:
        screenshot_note = (
            f"以下为 Coze 平台实际截图，包含知识库、合成状态表、工作流和运行结果。"
            f"H-02 技术材料与运行数量已满足：{coze_result['coze_acceptance_case_count']} 题 / "
            f"{coze_result['coze_acceptance_assistant_turn_count']} 个助手轮次；"
            f"原始冻结结果中 {coze_result['coze_partial_case_count']} 条答案为 partial。"
            f"另有 {coze_result['coze_supplemental_retest_count']} 条提示词修订后补充复测，"
            f"{coze_result['coze_supplemental_retest_pass_count']} 条通过、"
            f"{coze_result['coze_supplemental_retest_partial_count']} 条仍为 partial；"
            "Agent 保持未公开草稿；平台未展示的账单和逐轮工具 trace 不补写为已观察。\n\n"
            + "\n".join(f"- `{name}`" for name in copied_coze_images)
            + "\n"
        )
    else:
        screenshot_note = "此目录等待真实 Coze 工作空间截图；当前没有可归档的 PNG 平台截图。\n"
    (coze_screenshots / "README.txt").write_text(screenshot_note, encoding="utf-8")

    # 02: principles route source, runtime support, local data and route-specific evidence.
    for folder in ("src/campus", "src/core", "src/schema", "tests/campus"):
        if folder == "tests/campus":
            src = ROOT / folder
            dst = OUT / "02_Python_Version" / folder
            dst.mkdir(parents=True, exist_ok=True)
            for name in (
                "test_conversation_memory.py",
                "test_evaluation_metrics.py",
                "test_human_service_tool.py",
                "test_ingestion_chunking.py",
                "test_principle_agent.py",
                "test_retrieval.py",
                "test_status_tools.py",
            ):
                shutil.copy2(src / name, dst / name)
        else:
            copy_dir(folder, Path("02_Python_Version") / folder)
    for name in ("pyproject.toml", "uv.lock", ".env.example", "LICENSE"):
        copy_file(name, Path("02_Python_Version") / name)
    for folder in ("docs/campus", "data/campus"):
        copy_dir(folder, Path("02_Python_Version") / folder)
    for name in ("prompts/campus_system_v1.md", "prompts/campus_system_v2.md"):
        copy_file(name, Path("02_Python_Version") / name)
    for name in ("frozen_cases.json", "status_tool_contract.json", "metric_spec_v1.json", "human_service_contract.json"):
        copy_file(f"evaluation/{name}", Path("02_Python_Version") / "evaluation" / name)
    for name in (
        "run_campus_principles_windows.py",
        "run_campus_principles_multiturn_windows.py",
        "run_campus_index_windows.py",
        "clear_principle_memory_windows.py",
    ):
        copy_file(f"scripts/{name}", Path("02_Python_Version") / "scripts" / name)
    copy_file("tests/conftest.py", Path("02_Python_Version") / "tests/conftest.py")
    copy_route_runs("02_Python_Version")
    for name in (
        "Agent_Baseline.md",
        "RAG_Baseline.md",
        "Agent_Evaluation.md",
        "Optimization_Comparison.md",
    ):
        copy_file(f"reports/{name}", Path("02_Python_Version") / "reports" / name)

    # 03: full engineering snapshot and its own route traces.
    for folder in ("src", "tests", "docs", "data", "evaluation", "prompts", "TASK", "docker"):
        if (ROOT / folder).is_dir():
            copy_dir(folder, Path("03_AI_Coding_Version") / folder)
    for name in ("pyproject.toml", "uv.lock", ".env.example", "README.md", "LICENSE", "UPSTREAM.md", "compose.yaml", "langgraph.json"):
        if (ROOT / name).is_file():
            copy_file(name, Path("03_AI_Coding_Version") / name)
    for source in (ROOT / "scripts").glob("*.py"):
        if source.name in {"set_local_secret.py", "remove_local_budget_setting.py", "build_submission_package_windows.py"}:
            continue
        target = OUT / "03_AI_Coding_Version" / "scripts" / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    copy_route_runs("03_AI_Coding_Version")
    write_route_readmes()

    # 04: one complete, shared immutable evaluation evidence set.
    copy_dir("evaluation", "04_Evaluation/evaluation")
    copy_evaluation_runs()
    for name in (
        "Agent_Baseline.md",
        "Agent_Evaluation.md",
        "Failure_Analysis.md",
        "Optimization_Comparison.md",
        "Prompt_Comparison.md",
        "RAG_Baseline.md",
        "API_USAGE.jsonl",
        "API_REQUEST_EVENTS.jsonl",
        "API_USAGE_ADJUSTMENTS.jsonl",
        "windows-test-summary.json",
        "windows-test-summary-baseline.json",
        "WINDOWS_ENVIRONMENT.json",
        "PROGRESS.md",
        "HUMAN_TODO.md",
        "package-verification.json",
        "FINAL_AUDIT.md",
        "EXTERNAL_DEPENDENCIES.md",
        "评分表_V1_V2.csv",
        "评分说明.md",
        "three_track_comparison.csv",
        "Coze_Python_Engineering_Mapping.md",
    ):
        source_folder = "runs" if name.startswith("windows-test-summary") else "reports"
        source = ROOT / source_folder / name
        if source.is_file():
            target = OUT / "04_Evaluation" / "reports" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    copy_dir("TASK", "04_Evaluation/TASK")

    # 05: report and diagram assets; adjust only the copied report's relative links.
    for name in (
        "final_report.md",
        "21_day_alignment.md",
        "FINAL_AUDIT.md",
        "package-verification.json",
        "system_architecture.mmd",
        "request_flow.mmd",
        "optimization_quality_metrics.svg",
        "optimization_latency_metrics.svg",
        "Agent_Evaluation.md",
        "Failure_Analysis.md",
        "requirements_matrix.md",
        "报告待填写项.md",
    ):
        copy_file(f"reports/{name}", Path("05_Final_Report") / name)
    report_path = OUT / "05_Final_Report" / "final_report.md"
    report = report_path.read_text(encoding="utf-8")
    report = report.replace("../docs/campus/source_manifest.json", "../02_Python_Version/docs/campus/source_manifest.json")
    report = report.replace("../coze/source_manifest.csv", "../01_Coze_Version/coze/source_manifest.csv")
    report = report.replace("../coze/验收补齐清单.md", "../01_Coze_Version/coze/验收补齐清单.md")
    report = report.replace("../coze/screenshots/", "../01_Coze_Version/coze/screenshots/")
    report = report.replace("../coze/workflow/", "../01_Coze_Version/coze/workflow/")
    report = report.replace("../submission/06_Demo/screenshots/", "../06_Demo/screenshots/")
    report = report.replace("../runs/", "../04_Evaluation/runs/")
    report = report.replace(
        "[three_track_comparison.csv](three_track_comparison.csv)",
        "[three_track_comparison.csv](../04_Evaluation/reports/three_track_comparison.csv)",
    )
    report = report.replace(
        "](评分表_V1_V2.csv)",
        "](../04_Evaluation/reports/评分表_V1_V2.csv)",
    )
    report_path.write_text(report, encoding="utf-8")

    # 06: include only a real browser capture when one has been saved.
    copy_file("reports/demo_script.md", "06_Demo/demo_script.md")
    copy_file("reports/system_architecture.mmd", "06_Demo/system_architecture.mmd")
    (OUT / "06_Demo" / "screenshots").mkdir(exist_ok=True)
    screenshot_sources = (
        "campus_ui_home.png",
        "engineering_ui_home_20261008.png",
        "engineering_ui_status_20261008.png",
    )
    copied_screenshots = []
    for filename in screenshot_sources:
        screenshot_source = ROOT / "reports" / filename
        if screenshot_source.is_file():
            shutil.copy2(screenshot_source, OUT / "06_Demo" / "screenshots" / filename)
            copied_screenshots.append(filename)
    if copied_screenshots:
        screenshot_note = (
            "以下为 Windows 本地运行页面的真实浏览器截图，记录项目功能测试结果。"
            "请勿放入密钥或个人敏感信息。\n\n"
            + "\n".join(f"- `{name}`" for name in copied_screenshots)
            + "\n"
        )
    else:
        screenshot_note = "待从 Windows 本地运行页面保存真实截图；不得放入密钥或个人敏感信息。\n"
    (OUT / "06_Demo" / "screenshots" / "README.txt").write_text(
        screenshot_note, encoding="utf-8"
    )

    readme = """# 校园智能客服课程设计交付包

## 六类目录

1. `01_Coze_Version/`：Coze 知识库、模拟状态表、两个个人空间工作流及 Agent 草稿；H-02 技术交付项已具备真实配置、14 题/16 助手轮次与对照证据。原始冻结结果 5 条 partial 仍保留；提示词修订后另有 3 条复测（1 条通过、2 条 partial），原结果未覆盖。平台不可观测字段如实保留；Agent 未公开发布。
2. `02_Python_Version/`：独立 Python 显式 RAG/ToolRegistry 源码、依赖锁、来源、向量索引和 Principles 路线结果。
3. `03_AI_Coding_Version/`：长安大学校园客服 LangGraph/FastAPI/Streamlit 工程版、测试、依赖和 Engineering 路线结果；工程来源在 `UPSTREAM.md` 公开记录。
4. `04_Evaluation/`：冻结集、全部原始 runs/traces、指标、Judge、失败、用量与评分表。
5. `05_Final_Report/`：31 章课程设计报告、图表和项目范围说明。
6. `06_Demo/`：Windows 演示脚本和项目页面测试截图。

这是章峻炜（学号 2023900904）的个人课程设计项目，课程名称为“人工智能课程设计”，指导教师为宋清松，项目开始日期为 2026-10-01；项目没有小组分工。报告记录了实际实现、评测结果和未解决问题，不代表课程已经验收或教师已签收。V1/V2 各 5 份回答按统一 Rubric 评分均为 30/30，评分者为 Codex，评分理由和 trace 已归档。K01、K10、U02 三个不同检索问题均有失败证据；K01/K10 已修复，U02 仍未解决。

## 安全与复现

- 包内不包含 `.env`、`.venv`、`.git` 或 Python cache。`.env.example` 只含空配置字段；需要运行真实聊天时，在各路线本机单独安全配置。
- `.venv` 不打包；从各版根目录在 Windows PowerShell 按 README 用对应 `uv.lock`/`uv sync --frozen` 安装。
- 两条本地路线的安装/种子索引/启动方式各自记录；模型实时调用会计费。通用 UI 的 `/invoke` 响应不含 provider token usage，单次 UI 调用成本需查看服务商账单。Evaluation 离线重算使用已保存 trace。
- UI preview 的静态 manifest/AppTest 记录可供审阅；仍在运行的预览数据库和日志不打包。
- 通过 `package_manifest.json` 查看每个交付文件 SHA-256。任何更新评分、Coze 运行记录或截图后，应重新生成 manifest 并重新核对。
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")

    missing = [name for name in REQUIRED_DIRS if not (OUT / name).is_dir()]
    if missing:
        raise RuntimeError(f"Missing required submission directories: {missing}")
    forbidden = [
        path
        for path in OUT.rglob("*")
        if path.is_dir()
        and path.name in {".venv", ".git", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
        or path.is_file() and path.name == ".env"
    ]
    if forbidden:
        raise RuntimeError("Forbidden runtime/secret paths were copied into submission.")

    suspicious_files = []
    file_rows = []
    for path in sorted(p for p in OUT.rglob("*") if p.is_file() and p.name != "package_manifest.json"):
        raw = path.read_bytes()
        if SECRET_PATTERN.search(raw.decode("utf-8", errors="ignore")):
            if path.name != ".env.example":
                suspicious_files.append(str(path.relative_to(OUT)))
        file_rows.append(
            {
                "path": str(path.relative_to(OUT)).replace("\\", "/"),
                "size_bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    if suspicious_files:
        raise RuntimeError("Possible credential pattern found in package files; values were not printed.")

    manifest = {
        "created_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
        "status": "technical_package_complete_scope_limited",
        "platform": "win32",
        "directory_count": len(REQUIRED_DIRS),
        "directories": list(REQUIRED_DIRS),
        "file_count": len(file_rows),
        "contains_dotenv": False,
        "contains_virtual_environment": False,
        **coze_manifest_fields(),
        **rating_evidence_fields(),
        "technical_artifact_package_complete": True,
        "user_excluded_scope_items": ["personal identity/signature", "submitter live demo", "teacher permission"],
        "coze_publication_claimed": False,
        "teacher_permission_claimed": False,
        "distinct_retrieval_failure_count_confirmed": 3,
        "distinct_retrieval_failure_threshold": 3,
        "unresolved_retrieval_failure_count": 1,
        "files": file_rows,
    }
    (OUT / "package_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "directories": manifest["directory_count"],
                "files": manifest["file_count"],
                "contains_dotenv": False,
                **coze_manifest_fields(),
                **rating_evidence_fields(),
            },
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--refresh-manifest",
        action="store_true",
        help="Rehash and validate an existing submission/ package without copying or deleting files.",
    )
    args = parser.parse_args()
    if args.refresh_manifest:
        refresh_manifest()
    else:
        assemble()
