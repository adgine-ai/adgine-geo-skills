#!/usr/bin/env python3
"""Summarize GEO audit timings without slowing down the normal workflow.

Normal audits should use the `artifacts` command once at the end. It reads the
timings already written by the collector/scorer/visibility/PDF scripts and does
not add start/stop marker overhead to the workflow.

The legacy `start`/`mark` ledger commands are kept for deep debugging only.
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def _now() -> tuple[float, str]:
    timestamp = time.time()
    iso = datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
    return timestamp, iso


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def create_ledger(path: Path, *, label: str = "", metadata: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    timestamp, iso = _now()
    ledger = {
        "label": label,
        "metadata": metadata or {},
        "started_at": iso,
        "events": [
            {"name": "workflow_start", "timestamp": timestamp, "iso": iso, "metadata": {}}
        ],
        "attachments": {},
    }
    _write_json(path, ledger)
    return ledger


def mark_event(path: Path, name: str, *, metadata: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    ledger = _read_json(path)
    timestamp, iso = _now()
    ledger.setdefault("events", []).append({
        "name": name,
        "timestamp": timestamp,
        "iso": iso,
        "metadata": metadata or {},
    })
    _write_json(path, ledger)
    return ledger


def _extract_timings(payload: dict[str, Any]) -> dict[str, Any]:
    meta = payload.get("meta")
    if isinstance(meta, dict) and isinstance(meta.get("timings"), dict):
        return {
            "source": "meta.timings",
            "timings": meta["timings"],
            "total_seconds": meta.get("report_generation_elapsed_seconds") or meta["timings"].get("total_collection_seconds"),
        }
    if isinstance(payload.get("timings"), dict):
        return {
            "source": "timings",
            "timings": payload["timings"],
            "total_seconds": _first_total(payload["timings"]),
        }
    return {"source": "", "timings": {}, "total_seconds": None}


def _first_total(timings: dict[str, Any]) -> Optional[float]:
    for key in (
        "total_collection_seconds",
        "total_score_module_seconds",
        "total_visibility_prepare_seconds",
        "total_visibility_score_seconds",
        "total_pdf_module_seconds",
    ):
        if key in timings:
            try:
                return float(timings[key])
            except (TypeError, ValueError):
                return None
    return None


def attach_json(path: Path, name: str, json_path: Path) -> dict[str, Any]:
    ledger = _read_json(path)
    payload = _read_json(json_path)
    attachment = {
        "path": str(json_path.expanduser().absolute()),
    }
    attachment.update(_extract_timings(payload))
    ledger.setdefault("attachments", {})[name] = attachment
    _write_json(path, ledger)
    return ledger


def artifact_attachment(name: str, json_path: Optional[Path]) -> Optional[dict[str, Any]]:
    if not json_path:
        return None
    path = json_path.expanduser().absolute()
    if not path.exists():
        return {
            "path": str(path),
            "missing": True,
            "source": "",
            "timings": {},
            "total_seconds": None,
        }
    payload = _read_json(path)
    attachment = {
        "path": str(path),
        "missing": False,
        "modified_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
    }
    attachment.update(_extract_timings(payload))
    return attachment


def summarize_artifacts(
    *,
    label: str = "",
    collect_json: Optional[Path] = None,
    score_json: Optional[Path] = None,
    visibility_plan_json: Optional[Path] = None,
    visibility_results_json: Optional[Path] = None,
    pdf_timing_json: Optional[Path] = None,
    ui_elapsed_seconds: Optional[float] = None,
) -> dict[str, Any]:
    attachments: dict[str, Any] = {}
    for name, path in (
        ("collect", collect_json),
        ("score", score_json),
        ("visibility_prepare", visibility_plan_json),
        ("visibility_score", visibility_results_json),
        ("pdf", pdf_timing_json),
    ):
        attachment = artifact_attachment(name, path)
        if attachment:
            attachments[name] = attachment

    known_script_seconds = round(
        sum(
            float(item["total_seconds"])
            for item in attachments.values()
            if isinstance(item.get("total_seconds"), (int, float))
        ),
        3,
    )
    untracked_agent_overhead_seconds = None
    if ui_elapsed_seconds is not None:
        untracked_agent_overhead_seconds = round(float(ui_elapsed_seconds) - known_script_seconds, 3)

    artifact_timeline = sorted(
        [
            {
                "name": name,
                "modified_at": attachment["modified_at"],
                "path": attachment["path"],
            }
            for name, attachment in attachments.items()
            if attachment.get("modified_at")
        ],
        key=lambda item: item["modified_at"],
    )

    return {
        "label": label,
        "measurement_mode": "artifact_summary",
        "note": (
            "Low-overhead timing summary. It reads existing artifact timings once at the end. "
            "It does not measure full UI/agent elapsed time unless ui_elapsed_seconds is provided."
        ),
        "total_workflow_seconds": ui_elapsed_seconds,
        "known_script_seconds": known_script_seconds,
        "untracked_agent_overhead_seconds": untracked_agent_overhead_seconds,
        "artifact_timeline": artifact_timeline,
        "attachments": attachments,
    }


def summarize_ledger(ledger: dict[str, Any]) -> dict[str, Any]:
    events = ledger.get("events", [])
    spans: list[dict[str, Any]] = []
    for previous, current in zip(events, events[1:]):
        elapsed = float(current["timestamp"]) - float(previous["timestamp"])
        spans.append({
            "from": previous["name"],
            "to": current["name"],
            "seconds": round(elapsed, 3),
        })

    named_starts: dict[str, dict[str, Any]] = {}
    named_spans: list[dict[str, Any]] = []
    for event in events:
        name = str(event.get("name", ""))
        if name.endswith("_start"):
            named_starts[name[:-6]] = event
        elif name.endswith("_end"):
            key = name[:-4]
            start = named_starts.get(key)
            if start:
                named_spans.append({
                    "name": key,
                    "seconds": round(float(event["timestamp"]) - float(start["timestamp"]), 3),
                    "start": start.get("iso", ""),
                    "end": event.get("iso", ""),
                })

    total_seconds = None
    if events:
        total_seconds = round(float(events[-1]["timestamp"]) - float(events[0]["timestamp"]), 3)

    attachments = ledger.get("attachments", {})
    known_script_seconds = round(
        sum(
            float(item["total_seconds"])
            for item in attachments.values()
            if isinstance(item.get("total_seconds"), (int, float))
        ),
        3,
    )

    return {
        "label": ledger.get("label", ""),
        "metadata": ledger.get("metadata", {}),
        "started_at": ledger.get("started_at", ""),
        "total_workflow_seconds": total_seconds,
        "known_script_seconds": known_script_seconds,
        "named_spans": named_spans,
        "event_spans": spans,
        "attachments": attachments,
    }


def format_markdown_summary(summary: dict[str, Any]) -> str:
    if summary.get("measurement_mode") == "artifact_summary":
        lines = [
            f"# GEO Timing Debug: {summary.get('label') or 'workflow'}",
            "",
            summary.get("note", ""),
            "",
            f"**Workflow total**: {summary.get('total_workflow_seconds') if summary.get('total_workflow_seconds') is not None else 'not measured'}",
            f"**Known script-internal seconds**: {summary.get('known_script_seconds', '')}s",
        ]
        if summary.get("untracked_agent_overhead_seconds") is not None:
            lines.append(f"**Untracked agent/UI overhead**: {summary['untracked_agent_overhead_seconds']}s")

        timeline = summary.get("artifact_timeline", [])
        if timeline:
            lines.extend(["", "## Artifact Timeline", "", "| Artifact | Modified At | Path |", "|---|---|---|"])
            for item in timeline:
                lines.append(f"| {item['name']} | {item['modified_at']} | `{item['path']}` |")

        attachments = summary.get("attachments", {})
        if attachments:
            lines.extend([
                "",
                "## Script-Internal Timings",
                "",
                "These values come from each script's own timing block. They are not end-to-end phase durations.",
                "",
                "| Attachment | Source | Internal Total | Path |",
                "|---|---|---:|---|",
            ])
            for name, attachment in attachments.items():
                total = attachment.get("total_seconds")
                total_text = f"{float(total):.3f}s" if isinstance(total, (int, float)) else ""
                lines.append(
                    f"| {name} | {attachment.get('source', '')} | {total_text} | `{attachment.get('path', '')}` |"
                )
        return "\n".join(lines) + "\n"

    lines = [
        f"# GEO Timing Debug: {summary.get('label') or 'workflow'}",
        "",
        f"**Started at**: {summary.get('started_at', '')}",
        f"**Workflow total**: {summary.get('total_workflow_seconds')}s",
        f"**Known script seconds**: {summary.get('known_script_seconds', '')}s",
        "",
        "## Named Spans",
        "",
        "| Step | Seconds |",
        "|---|---:|",
    ]
    for span in summary.get("named_spans", []):
        lines.append(f"| {span['name']} | {span['seconds']:.3f}s |")

    attachments = summary.get("attachments", {})
    if attachments:
        lines.extend(["", "## Attached Script Timings", "", "| Attachment | Source | Total | Path |", "|---|---|---:|---|"])
        for name, attachment in attachments.items():
            total = attachment.get("total_seconds")
            total_text = f"{float(total):.3f}s" if isinstance(total, (int, float)) else ""
            lines.append(
                f"| {name} | {attachment.get('source', '')} | {total_text} | `{attachment.get('path', '')}` |"
            )
    return "\n".join(lines) + "\n"


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Track and summarize GEO audit workflow timings.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="Create a new timing ledger")
    start.add_argument("ledger_json")
    start.add_argument("--label", default="")
    start.add_argument("--metadata-json", default="{}")

    mark = subparsers.add_parser("mark", help="Append a timing event")
    mark.add_argument("ledger_json")
    mark.add_argument("name")
    mark.add_argument("--metadata-json", default="{}")

    attach = subparsers.add_parser("attach", help="Attach a JSON artifact and extract its timings")
    attach.add_argument("ledger_json")
    attach.add_argument("name")
    attach.add_argument("json_path")

    summary = subparsers.add_parser("summary", help="Summarize a timing ledger")
    summary.add_argument("ledger_json")
    summary.add_argument("--output", "-o")
    summary.add_argument("--report")

    artifacts = subparsers.add_parser("artifacts", help="Build a low-overhead timing summary from existing artifact JSON files")
    artifacts.add_argument("--label", default="")
    artifacts.add_argument("--collect-json")
    artifacts.add_argument("--score-json")
    artifacts.add_argument("--visibility-plan-json")
    artifacts.add_argument("--visibility-results-json")
    artifacts.add_argument("--pdf-timing-json")
    artifacts.add_argument("--ui-elapsed-seconds", type=float, help="Optional UI-reported elapsed seconds, if available")
    artifacts.add_argument("--output", "-o")
    artifacts.add_argument("--report")

    args = parser.parse_args(argv)

    if args.command == "start":
        metadata = json.loads(args.metadata_json)
        create_ledger(Path(args.ledger_json), label=args.label, metadata=metadata)
        return 0

    if args.command == "mark":
        metadata = json.loads(args.metadata_json)
        mark_event(Path(args.ledger_json), args.name, metadata=metadata)
        return 0

    if args.command == "attach":
        attach_json(Path(args.ledger_json), args.name, Path(args.json_path))
        return 0

    if args.command == "summary":
        result = summarize_ledger(_read_json(Path(args.ledger_json)))
        if args.output:
            _write_json(Path(args.output), result)
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.report:
            Path(args.report).expanduser().absolute().write_text(format_markdown_summary(result), encoding="utf-8")
        return 0

    if args.command == "artifacts":
        result = summarize_artifacts(
            label=args.label,
            collect_json=Path(args.collect_json) if args.collect_json else None,
            score_json=Path(args.score_json) if args.score_json else None,
            visibility_plan_json=Path(args.visibility_plan_json) if args.visibility_plan_json else None,
            visibility_results_json=Path(args.visibility_results_json) if args.visibility_results_json else None,
            pdf_timing_json=Path(args.pdf_timing_json) if args.pdf_timing_json else None,
            ui_elapsed_seconds=args.ui_elapsed_seconds,
        )
        if args.output:
            _write_json(Path(args.output), result)
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.report:
            Path(args.report).expanduser().absolute().write_text(format_markdown_summary(result), encoding="utf-8")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
