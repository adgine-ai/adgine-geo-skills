"""Render stable report dictionaries as Markdown and standalone offline HTML."""

import copy
import html
import json
import math
import os
import re
from datetime import datetime, timezone


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _escape(value):
    return html.escape("" if value is None else str(value), quote=True)


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def format_value(value, fmt=None):
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    number = _number(value)
    if fmt in ("percent", "percentage") and number is not None:
        return f"{number:,.1f}%"
    if fmt in ("integer", "count", "rank") and number is not None:
        prefix = "#" if fmt == "rank" else ""
        return f"{prefix}{number:,.0f}"
    if fmt == "bytes" and number is not None:
        units = ["B", "KB", "MB", "GB", "TB"]
        index = 0
        while abs(number) >= 1024 and index < len(units) - 1:
            number /= 1024
            index += 1
        return f"{number:,.1f} {units[index]}"
    if fmt == "seconds" and number is not None:
        return f"{number:,.1f}s"
    if number is not None and isinstance(value, float):
        return f"{number:,.2f}".rstrip("0").rstrip(".")
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def _delta(metric):
    change = metric.get("change")
    if change is None:
        return ""
    number = _number(change)
    rendered = format_value(abs(number) if number is not None else change, metric.get("change_format") or metric.get("format"))
    sign = "+" if number is not None and number > 0 else ("−" if number is not None and number < 0 else "")
    return f"{sign}{rendered} vs previous period"


def _render_metrics(metrics):
    output = []
    for metric in metrics or []:
        direction = metric.get("direction") or ""
        note = metric.get("note")
        output.append(
            '<article class="metric">'
            f'<div class="metric-label">{_escape(metric.get("label"))}</div>'
            f'<div class="metric-value">{_escape(format_value(metric.get("value"), metric.get("format")))}</div>'
            f'<div class="metric-delta {direction}">{_escape(_delta(metric) or note or "")}</div>'
            "</article>"
        )
    return "".join(output)


def _chart_size(count):
    return 720, max(220, min(620, 74 + count * 32))


def _render_bar(chart):
    items = chart.get("items") or []
    width, height = _chart_size(len(items))
    label_width, right, top, row_h = 230, 60, 26, 30
    values = [_number(item.get("value")) or 0 for item in items]
    maximum = max([abs(item) for item in values] + [1])
    plot_width = width - label_width - right
    rows = []
    for index, (item, value) in enumerate(zip(items, values)):
        y = top + index * row_h
        bar_width = max(1, abs(value) / maximum * plot_width)
        color = "#2563eb" if item.get("highlight") else item.get("color") or "#60a5fa"
        label = str(item.get("label") or "")
        rows.append(
            f'<text x="0" y="{y + 17}" class="svg-label"><title>{_escape(label)}</title>{_escape(label[:38])}</text>'
            f'<rect x="{label_width}" y="{y + 3}" width="{bar_width:.1f}" height="20" rx="5" fill="{_escape(color)}" />'
            f'<text x="{min(width - right + 6, label_width + bar_width + 7):.1f}" y="{y + 18}" class="svg-value">{_escape(format_value(item.get("value"), chart.get("format")))}</text>'
        )
    return f'<svg viewBox="0 0 {width} {height}" role="img">{"".join(rows)}</svg>'


def _render_line(chart):
    series = chart.get("series") or []
    all_points = [point for item in series for point in (item.get("points") or []) if _number(point.get("y")) is not None]
    if not all_points:
        return '<div class="empty">No trend data</div>'
    width, height = 760, 300
    left, right, top, bottom = 54, 24, 24, 44
    values = [_number(point.get("y")) for point in all_points]
    low, high = min(values), max(values)
    if math.isclose(low, high):
        low -= 1
        high += 1
    count = max(len(item.get("points") or []) for item in series)
    x_span, y_span = width - left - right, height - top - bottom
    paths = []
    colors = ["#2563eb", "#06b6d4", "#8b5cf6", "#f59e0b", "#10b981"]
    for series_index, item in enumerate(series):
        coords = []
        for index, point in enumerate(item.get("points") or []):
            value = _number(point.get("y"))
            if value is None:
                continue
            x = left + (index / max(count - 1, 1)) * x_span
            y = top + (high - value) / (high - low) * y_span
            coords.append((x, y, point))
        if not coords:
            continue
        path = " ".join(("M" if index == 0 else "L") + f" {x:.1f} {y:.1f}" for index, (x, y, _) in enumerate(coords))
        color = item.get("color") or colors[series_index % len(colors)]
        dots = "".join(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{color}"><title>{_escape(point.get("x"))}: {_escape(format_value(point.get("y"), chart.get("format")))}</title></circle>'
            for x, y, point in coords
        )
        paths.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="3" />{dots}')
    axes = (
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" class="axis" />'
        f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" class="axis" />'
        f'<text x="4" y="{top+7}" class="svg-value">{_escape(format_value(high, chart.get("format")))}</text>'
        f'<text x="4" y="{height-bottom}" class="svg-value">{_escape(format_value(low, chart.get("format")))}</text>'
    )
    legend = "".join(
        f'<span><i style="background:{_escape(item.get("color") or colors[index % len(colors)])}"></i>{_escape(item.get("name"))}</span>'
        for index, item in enumerate(series)
    )
    return f'<div class="legend">{legend}</div><svg viewBox="0 0 {width} {height}" role="img">{axes}{"".join(paths)}</svg>'


def _render_heatmap(chart):
    columns = chart.get("columns") or []
    rows = chart.get("rows") or []
    values = [_number(value) for row in rows for value in (row.get("values") or {}).values()]
    values = [value for value in values if value is not None]
    maximum = max(values + [1])
    head = "".join(f"<th>{_escape(item)}</th>" for item in columns)
    body = []
    for row in rows:
        cells = []
        for column in columns:
            value = _number((row.get("values") or {}).get(column))
            alpha = .08 if value is None else .12 + .72 * max(0, value) / maximum
            cells.append(f'<td><div class="heat" style="background:rgba(37,99,235,{alpha:.2f})">{_escape(format_value(value, chart.get("format")))}</div></td>')
        klass = "highlight" if row.get("highlight") else ""
        body.append(f'<tr class="{klass}"><th>{_escape(row.get("label"))}</th>{"".join(cells)}</tr>')
    return f'<div class="table-wrap"><table><thead><tr><th>Brand</th>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def _render_charts(charts):
    output = []
    for chart in charts or []:
        chart_type = chart.get("type") or "bar"
        if chart_type == "line":
            body = _render_line(chart)
        elif chart_type == "heatmap":
            body = _render_heatmap(chart)
        else:
            body = _render_bar(chart)
        output.append(f'<section class="panel chart-panel"><h2>{_escape(chart.get("title"))}</h2><div class="chart">{body}</div></section>')
    return "".join(output)


def _render_tables(tables):
    output = []
    for table in tables or []:
        columns = table.get("columns") or []
        rows = table.get("rows") or []
        header = "".join(
            f'<th class="{"num" if column.get("align") == "right" else ""}">{_escape(column.get("label") or column.get("key"))}</th>'
            for column in columns
        )
        body = []
        for row in rows:
            klass = "highlight" if row.get("_highlight") else ""
            cells = "".join(
                f'<td class="{"num" if column.get("align") == "right" else ""}">{_escape(format_value(row.get(column.get("key")), column.get("format")))}</td>'
                for column in columns
            )
            body.append(f'<tr class="{klass}">{cells}</tr>')
        note = f'<p class="note">{_escape(table.get("note"))}</p>' if table.get("note") else ""
        empty = '<div class="empty">No data for this section</div>'
        content = f'<div class="table-wrap"><table><thead><tr>{header}</tr></thead><tbody>{"".join(body)}</tbody></table></div>' if rows else empty
        output.append(f'<section class="panel"><h2>{_escape(table.get("title"))}</h2>{note}{content}</section>')
    return "".join(output)


def _render_insights(insights):
    if not insights:
        return ""
    items = []
    for item in insights:
        if isinstance(item, dict):
            title = item.get("title")
            body = item.get("body") or item.get("text")
            text = f"{title}: {body}" if title else body
        else:
            text = item
        items.append(f"<li>{_escape(text)}</li>")
    return f'<section class="panel insights-panel"><h2>Key findings</h2><ul class="insights">{"".join(items)}</ul></section>'


def _render_coverage(coverage):
    if not coverage:
        return ""
    rows = []
    for item in coverage.get("sources") or []:
        status = item.get("status") or "ok"
        rows.append(
            f'<tr><td>{_escape(item.get("name"))}</td><td><span class="status {status}">{_escape(status)}</span></td>'
            f'<td>{_escape(item.get("as_of") or "—")}</td><td>{_escape(item.get("unit") or "—")}</td></tr>'
        )
    requested = coverage.get("requested_range") or {}
    note = f'Requested range: {_escape(requested.get("from"))} → {_escape(requested.get("to"))}'
    return (
        '<section class="panel"><h2>Data coverage</h2>'
        f'<p class="note">{note}</p><div class="table-wrap"><table><thead><tr>'
        '<th>Source</th><th>Status</th><th>As of</th><th>Unit</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div></section>'
    )


def _render_audit(audit):
    fields = audit.get("fields") or []
    calls = audit.get("api_calls") or []
    warnings = audit.get("warnings") or []
    items = "".join(f'<div class="audit-key">{_escape(item.get("label"))}</div><div>{_escape(item.get("value"))}</div>' for item in fields)
    call_rows = "".join(
        f'<tr><td>{_escape(item.get("path"))}</td><td class="num">{_escape(item.get("duration_ms"))} ms</td><td>{_escape(item.get("status") or "ok")}</td></tr>'
        for item in calls
    )
    warning_list = "".join(f"<li>{_escape(item)}</li>" for item in warnings)
    return (
        '<section class="panel"><details><summary>Query audit and data quality</summary>'
        f'<div class="audit-grid">{items}</div>'
        f'<ul class="warnings">{warning_list}</ul>'
        '<div class="table-wrap"><table><thead><tr><th>API path</th><th class="num">Duration</th><th>Status</th></tr></thead>'
        f'<tbody>{call_rows}</tbody></table></div></details></section>'
    )


def render_html(report, template_path=None):
    if template_path is None:
        template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "report-template.html")
    with open(template_path, encoding="utf-8") as handle:
        template = handle.read()
    context = "".join(
        f'<span><b>{_escape(item.get("label"))}</b> {_escape(item.get("value"))}</span>'
        for item in report.get("context") or []
    )
    public_report = copy.deepcopy(report)
    public_report.pop("next_actions", None)
    embedded = json.dumps(public_report, ensure_ascii=False).replace("</", "<\\/")
    values = {
        "TITLE": _escape(report.get("title")),
        "SUBTITLE": _escape(report.get("subtitle")),
        "GENERATED_AT": _escape(report.get("generated_at")),
        "CONTEXT": context,
        "METRICS": _render_metrics(report.get("metrics")),
        "CHARTS": _render_charts(report.get("charts")),
        "TABLES": _render_tables(report.get("tables")),
        "INSIGHTS": _render_insights(report.get("insights")),
        "COVERAGE": _render_coverage(report.get("coverage")),
        "AUDIT": _render_audit(report.get("audit") or {}),
        "SCHEMA_VERSION": _escape(report.get("schema_version")),
        "EMBEDDED_JSON": embedded,
    }
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def _safe_filename(value):
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(value or "report")).strip("-.")
    return value or "report"


def write_html(report, output=None, output_dir=None):
    if output:
        path = os.path.abspath(output)
    else:
        directory = os.path.abspath(output_dir or os.environ.get("GEO_REPORT_DIR") or os.path.join(os.getcwd(), "adgine-reports"))
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = os.path.join(directory, f"{_safe_filename(report.get('report_type'))}-{stamp}.html")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(render_html(report))
    return path


def render_markdown(report):
    lines = [f"# {report.get('title')}", "", report.get("subtitle") or "", ""]
    if report.get("context"):
        lines.extend(["## Context", ""])
        lines.extend(f"- {item.get('label')}: {item.get('value')}" for item in report["context"])
        lines.append("")
    if report.get("metrics"):
        lines.extend(["## Metrics", "", "| Metric | Value | Change |", "|---|---:|---:|"])
        for metric in report["metrics"]:
            lines.append(f"| {metric.get('label')} | {format_value(metric.get('value'), metric.get('format'))} | {_delta(metric) or '—'} |")
        lines.append("")
    for table in report.get("tables") or []:
        columns = table.get("columns") or []
        lines.extend([f"## {table.get('title')}", ""])
        lines.append("| " + " | ".join(str(item.get("label") or item.get("key")) for item in columns) + " |")
        lines.append("| " + " | ".join("---:" if item.get("align") == "right" else "---" for item in columns) + " |")
        for row in table.get("rows") or []:
            lines.append("| " + " | ".join(format_value(row.get(item.get("key")), item.get("format")).replace("|", "\\|") for item in columns) + " |")
        lines.append("")
    if report.get("insights"):
        lines.extend(["## Key findings", ""])
        for item in report["insights"]:
            text = item.get("body") if isinstance(item, dict) else item
            lines.append(f"- {text}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
