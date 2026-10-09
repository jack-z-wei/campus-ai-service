"""Generate report-ready SVG charts from the saved Windows evaluation metrics."""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BASELINE_DEFAULT = "frozen-eval-v1-20261006"
OPTIMIZED_DEFAULT = "frozen-eval-optimized-v1-20261006"
ROUTES = (("principles", "Python 原理版"), ("engineering", "LangGraph 工程版"))


def read_metrics(run_id: str) -> dict:
    path = ROOT / "runs" / run_id / "metric_results.json"
    if not path.is_file():
        raise SystemExit(f"Missing metric results: {path}")
    result = json.loads(path.read_text(encoding="utf-8"))
    if result.get("answer_judge_pending"):
        raise SystemExit(f"Answer judge is still pending for {run_id}.")
    return result


def _text(x: float) -> str:
    return f"{x * 100:.1f}%"


def _quality_value(metrics: dict, route: str, key: str) -> float:
    item = metrics["implementations"][route]
    if key == "retrieval_at_5":
        return item["retrieval"]["metrics"]["recall_at_5"]["mean"]
    if key == "tool_selection":
        value = item["agent"]["tool_selection_accuracy"]
        return value["numerator"] / value["denominator"]
    if key == "task_completion":
        value = item["agent"]["task_completion_rate"]
        return value["numerator"] / value["denominator"]
    if key == "answer_correctness":
        return item["answer"]["correctness"]["complete_mean"]
    raise KeyError(key)


def quality_chart(baseline: dict, optimized: dict, output: Path) -> None:
    width, height = 1160, 620
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<style>text{font-family:"Microsoft YaHei","Noto Sans CJK SC",sans-serif;fill:#17212b}.small{font-size:13px}.label{font-size:14px}.title{font-size:24px;font-weight:700}.subtitle{font-size:14px;fill:#52616b}</style>',
        '<text x="36" y="40" class="title">优化前后固定集质量指标</text>',
        '<text x="36" y="66" class="subtitle">同一冻结集；分母和 N/A 口径见 reports/Agent_Evaluation.md</text>',
    ]
    groups = [
        ("retrieval_at_5", "Recall@5"),
        ("tool_selection", "工具选择"),
        ("task_completion", "任务完成"),
        ("answer_correctness", "答案正确性†"),
    ]
    panel_xs = (38, 592)
    panel_width = 530
    plot_top, plot_height = 132, 340
    for (route, title), panel_x in zip(ROUTES, panel_xs, strict=True):
        parts.append(
            f'<text x="{panel_x + 8}" y="104" class="label" font-weight="700">{html.escape(title)}</text>'
        )
        plot_left = panel_x + 46
        plot_width = panel_width - 58
        for step in range(5):
            fraction = step / 4
            y = plot_top + plot_height * (1 - fraction)
            parts.append(
                f'<line x1="{plot_left}" y1="{y:.1f}" x2="{plot_left + plot_width}" y2="{y:.1f}" stroke="#dfe5e8"/>'
            )
            parts.append(
                f'<text x="{plot_left - 8}" y="{y + 5:.1f}" text-anchor="end" class="small">{fraction:.0%}</text>'
            )
        group_width = plot_width / len(groups)
        bar_width, bar_gap = 28, 7
        for index, (key, label) in enumerate(groups):
            center = plot_left + group_width * (index + 0.5)
            values = (_quality_value(baseline, route, key), _quality_value(optimized, route, key))
            for variant, value in enumerate(values):
                x = center - bar_width - bar_gap / 2 + variant * (bar_width + bar_gap)
                bar_h = max(0, min(1, value)) * plot_height
                y = plot_top + plot_height - bar_h
                color = "#4d78a8" if variant == 0 else "#f28e2b"
                parts.append(
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width}" height="{bar_h:.1f}" rx="3" fill="{color}"/>'
                )
                parts.append(
                    f'<text x="{x + bar_width / 2:.1f}" y="{y - 7:.1f}" text-anchor="middle" class="small">{_text(value)}</text>'
                )
            parts.append(
                f'<text x="{center:.1f}" y="{plot_top + plot_height + 25}" text-anchor="middle" class="label">{html.escape(label)}</text>'
            )
    parts.extend(
        [
            '<rect x="404" y="525" width="16" height="16" fill="#4d78a8"/><text x="428" y="538" class="label">基线</text>',
            '<rect x="500" y="525" width="16" height="16" fill="#f28e2b"/><text x="524" y="538" class="label">优化版</text>',
            '<text x="36" y="575" class="small">† Judge 与生成模型同系列；V1/V2 专项 Rubric 评分各 30/30，见评分表。</text>',
            "</svg>",
        ]
    )
    output.write_text("\n".join(parts) + "\n", encoding="utf-8")


def latency_chart(baseline: dict, optimized: dict, output: Path) -> None:
    width, height = 1160, 620
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<style>text{font-family:"Microsoft YaHei","Noto Sans CJK SC",sans-serif;fill:#17212b}.small{font-size:13px}.label{font-size:14px}.title{font-size:24px;font-weight:700}.subtitle{font-size:14px;fill:#52616b}</style>',
        '<text x="36" y="40" class="title">优化前后延迟（毫秒）</text>',
        '<text x="36" y="66" class="subtitle">每条路线各 23 个 turn；单次冻结集运行，不作性能显著性结论</text>',
    ]
    panel_xs = (38, 592)
    panel_width = 530
    plot_top, plot_height = 142, 330
    for (route, title), panel_x in zip(ROUTES, panel_xs, strict=True):
        baseline_item = baseline["implementations"][route]["engineering"]
        optimized_item = optimized["implementations"][route]["engineering"]
        values = (
            baseline_item["average_latency_ms"],
            optimized_item["average_latency_ms"],
            baseline_item["p95_latency_ms_nearest_rank"],
            optimized_item["p95_latency_ms_nearest_rank"],
        )
        max_value = max(values) * 1.15
        parts.append(
            f'<text x="{panel_x + 8}" y="108" class="label" font-weight="700">{html.escape(title)}</text>'
        )
        if route == "principles":
            scope = "检索 + API 往返"
        else:
            scope = "LangGraph ainvoke 墙钟时间"
        parts.append(f'<text x="{panel_x + 8}" y="128" class="small">测量范围：{scope}</text>')
        plot_left = panel_x + 50
        plot_width = panel_width - 64
        for step in range(5):
            fraction = step / 4
            y = plot_top + plot_height * (1 - fraction)
            parts.append(
                f'<line x1="{plot_left}" y1="{y:.1f}" x2="{plot_left + plot_width}" y2="{y:.1f}" stroke="#dfe5e8"/>'
            )
            parts.append(
                f'<text x="{plot_left - 8}" y="{y + 5:.1f}" text-anchor="end" class="small">{int(max_value * fraction)}</text>'
            )
        group_centers = (plot_left + plot_width * 0.30, plot_left + plot_width * 0.72)
        labels = ("平均", "P95")
        grouped_values = ((values[0], values[1]), (values[2], values[3]))
        bar_width, bar_gap = 40, 8
        for center, label, pair in zip(group_centers, labels, grouped_values, strict=True):
            for variant, value in enumerate(pair):
                x = center - bar_width - bar_gap / 2 + variant * (bar_width + bar_gap)
                bar_h = value / max_value * plot_height
                y = plot_top + plot_height - bar_h
                color = "#4d78a8" if variant == 0 else "#f28e2b"
                parts.append(
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width}" height="{bar_h:.1f}" rx="3" fill="{color}"/>'
                )
                parts.append(
                    f'<text x="{x + bar_width / 2:.1f}" y="{y - 7:.1f}" text-anchor="middle" class="small">{value:.0f}</text>'
                )
            parts.append(
                f'<text x="{center:.1f}" y="{plot_top + plot_height + 25}" text-anchor="middle" class="label">{label}</text>'
            )
    parts.extend(
        [
            '<rect x="404" y="525" width="16" height="16" fill="#4d78a8"/><text x="428" y="538" class="label">基线</text>',
            '<rect x="500" y="525" width="16" height="16" fill="#f28e2b"/><text x="524" y="538" class="label">优化版</text>',
            '<text x="36" y="575" class="small">P95 使用最近秩；两条路线测量范围不同，横跨路线不作直接快慢比较。</text>',
            "</svg>",
        ]
    )
    output.write_text("\n".join(parts) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-run-id", default=BASELINE_DEFAULT)
    parser.add_argument("--optimized-run-id", default=OPTIMIZED_DEFAULT)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports")
    args = parser.parse_args()
    if sys.platform != "win32":
        raise SystemExit("Generate evaluation report charts with the Windows project .venv.")
    baseline = read_metrics(args.baseline_run_id)
    optimized = read_metrics(args.optimized_run_id)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    quality_chart(baseline, optimized, args.output_dir / "optimization_quality_metrics.svg")
    latency_chart(baseline, optimized, args.output_dir / "optimization_latency_metrics.svg")
    print(
        json.dumps(
            {
                "baseline_run_id": args.baseline_run_id,
                "optimized_run_id": args.optimized_run_id,
                "charts": [
                    "optimization_quality_metrics.svg",
                    "optimization_latency_metrics.svg",
                ],
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
