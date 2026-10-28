#!/usr/bin/env python3
"""Shared data contracts and HTML rendering for Content Operations Workspace."""
from __future__ import annotations

import csv
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from html import escape
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
CALENDAR_FIELDS = [
    "content_id", "content_group_id", "title", "platform", "format", "theme",
    "planned_date", "status", "draft_path", "published_date", "published_url",
    "cta_url", "source_reference", "last_updated", "notes",
]
PERFORMANCE_FIELDS = [
    "performance_id", "content_id", "platform", "observed_date", "metric_basis",
    "impressions", "views", "reads", "likes", "comments", "shares", "clicks",
    "downloads", "installs", "source_reference", "notes",
]
METRICS = ["impressions", "views", "reads", "likes", "comments", "shares", "clicks", "downloads", "installs"]
STATUSES = {"Idea", "Planned", "Drafting", "Ready", "Scheduled", "Published", "Paused", "Cancelled"}
METRIC_BASES = {"", "Cumulative", "Period"}


def read_csv(path, expected_fields):
    path = Path(path)
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        if fields != expected_fields:
            raise ValueError(f"{path.name}: expected columns {','.join(expected_fields)}")
        return [{key: (value or "").strip() for key, value in row.items()} for row in reader]


def write_csv(path, fields, rows):
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def valid_date(value):
    if not value:
        return True
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def valid_url(value):
    if not value:
        return True
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def number(value):
    if value == "":
        return None
    try:
        parsed = Decimal(value.replace(",", ""))
    except (InvalidOperation, AttributeError):
        raise ValueError(f"invalid number '{value}'")
    if parsed < 0:
        raise ValueError(f"negative number '{value}'")
    return parsed


def validate_workspace(workspace):
    workspace = Path(workspace)
    errors = []
    try:
        calendar = read_csv(workspace / "content-calendar.csv", CALENDAR_FIELDS)
    except (OSError, ValueError) as error:
        return [str(error)], [], []
    try:
        performance = read_csv(workspace / "performance.csv", PERFORMANCE_FIELDS)
    except (OSError, ValueError) as error:
        return [str(error)], calendar, []

    ids = set()
    by_id = {}
    for row_number, row in enumerate(calendar, 2):
        label = f"content-calendar.csv row {row_number}"
        if not row["content_id"]:
            errors.append(f"{label}: content_id is required")
        elif row["content_id"] in ids:
            errors.append(f"{label}: duplicate content_id {row['content_id']}")
        else:
            ids.add(row["content_id"])
            by_id[row["content_id"]] = row
        for field in ("title", "platform", "status"):
            if not row[field]:
                errors.append(f"{label}: {field} is required")
        if row["status"] and row["status"] not in STATUSES:
            errors.append(f"{label}: unsupported status {row['status']}")
        for field in ("planned_date", "published_date", "last_updated"):
            if not valid_date(row[field]):
                errors.append(f"{label}: invalid {field} {row[field]}")
        if row["status"] == "Published" and not row["published_date"]:
            errors.append(f"{label}: Published requires published_date")
        for field in ("published_url", "cta_url"):
            if not valid_url(row[field]):
                errors.append(f"{label}: invalid {field}")
        if row["draft_path"]:
            draft = (workspace.parent / row["draft_path"]).resolve()
            if workspace.parent.resolve() not in draft.parents or not draft.is_file():
                errors.append(f"{label}: missing or unsafe draft_path {row['draft_path']}")

    performance_ids = set()
    logical_keys = set()
    for row_number, row in enumerate(performance, 2):
        label = f"performance.csv row {row_number}"
        if not row["performance_id"]:
            errors.append(f"{label}: performance_id is required")
        elif row["performance_id"] in performance_ids:
            errors.append(f"{label}: duplicate performance_id {row['performance_id']}")
        else:
            performance_ids.add(row["performance_id"])
        content = by_id.get(row["content_id"])
        if not content:
            errors.append(f"{label}: unknown content_id {row['content_id']}")
        elif row["platform"] != content["platform"]:
            errors.append(f"{label}: platform does not match {content['title']}")
        if not row["platform"]:
            errors.append(f"{label}: platform is required")
        if not row["observed_date"] or not valid_date(row["observed_date"]):
            errors.append(f"{label}: valid observed_date is required")
        if row["metric_basis"] not in METRIC_BASES:
            errors.append(f"{label}: metric_basis must be Cumulative, Period or blank")
        known = 0
        for metric in METRICS:
            try:
                if number(row[metric]) is not None:
                    known += 1
            except ValueError as error:
                errors.append(f"{label}: {metric} has {error}")
        if not known:
            errors.append(f"{label}: at least one metric is required")
        key = (row["content_id"], row["observed_date"], row["metric_basis"])
        if all(key):
            if key in logical_keys:
                errors.append(f"{label}: duplicate snapshot for {row['content_id']} on {row['observed_date']}")
            logical_keys.add(key)
    return errors, calendar, performance


def fmt_number(value):
    if value == "":
        return "N/A"
    parsed = number(value)
    if parsed == parsed.to_integral():
        return f"{int(parsed):,}"
    return f"{parsed:,.2f}".rstrip("0").rstrip(".")


def badge(value):
    cls = "good" if value == "Published" else "warn" if value in {"Ready", "Scheduled"} else "neutral"
    return f'<span class="badge {cls}">{escape(value)}</span>'


def empty(message):
    return f'<div class="empty">{escape(message)}</div>'


def donut(counts):
    total = sum(counts.values())
    if not total:
        return empty("No content records yet, so no status distribution is shown.")
    colors = ["#356a57", "#c47b56", "#6d749f", "#a76b87", "#9b7a37", "#577f91", "#86755f", "#9b5a5a"]
    circumference = 2 * 3.1415926535 * 72
    offset = 0.0
    circles = []
    legend = []
    for index, (label, count) in enumerate(sorted(counts.items())):
        length = circumference * count / total
        color = colors[index % len(colors)]
        circles.append(f'<circle cx="110" cy="110" r="72" fill="none" stroke="{color}" stroke-width="24" stroke-dasharray="{length:.3f} {circumference-length:.3f}" stroke-dashoffset="{-offset:.3f}"/>')
        legend.append(f'<div class="legend-item"><span class="swatch" style="background:{color}"></span><span><b>{escape(label)}</b><small>{count} · {count/total:.0%}</small></span></div>')
        offset += length
    return f'''<div class="chart-layout"><div class="donut-wrap"><svg class="donut" viewBox="0 0 220 220" role="img" aria-label="Content status distribution"><circle cx="110" cy="110" r="72" fill="none" stroke="#e8e2d8" stroke-width="24"/><g transform="rotate(-90 110 110)">{''.join(circles)}</g><text x="110" y="105" text-anchor="middle" class="chart-value">{total}</text><text x="110" y="126" text-anchor="middle" class="chart-label">Content</text></svg></div><div class="legend">{''.join(legend)}</div></div>'''


def bars(counts):
    if not counts:
        return empty("No content records yet, so no platform distribution is shown.")
    maximum = max(counts.values()) or 1
    colors = ["#356a57", "#577f91", "#c47b56", "#6d749f", "#a76b87"]
    out = []
    for index, (label, count) in enumerate(sorted(counts.items())):
        out.append(f'<div class="bar-row"><div class="bar-heading"><b>{escape(label)}</b><span>{count}</span></div><div class="bar-track"><i style="width:{100*count/maximum:.1f}%;background:{colors[index%len(colors)]}"></i></div></div>')
    return '<div class="bar-chart">' + ''.join(out) + '</div>'


def next_actions(calendar, performance):
    if not calendar:
        return ["Describe a content goal or attach local materials to create the first plan."]
    perf_by_content = {}
    for row in performance:
        perf_by_content.setdefault(row["content_id"], []).append(row)
    actions = []
    for row in sorted(calendar, key=lambda item: (item["planned_date"] or "9999-99-99", item["title"])):
        title = row["title"]
        platform = row["platform"]
        status = row["status"]
        if status in {"Idea", "Planned"}:
            actions.append(f'Draft “{title}” for {platform}.')
        elif status == "Drafting":
            actions.append(f'Finish and review the {platform} draft “{title}”.')
        elif status == "Ready":
            actions.append(f'Review “{title}” and decide whether to schedule it for {platform}.')
        elif status == "Scheduled":
            date_text = f' on {row["planned_date"]}' if row["planned_date"] else ""
            actions.append(f'Confirm whether “{title}” was actually published to {platform}{date_text}; do not advance it automatically.')
        elif status == "Published" and not perf_by_content.get(row["content_id"]):
            actions.append(f'“{title}” is published on {platform} but has no recorded results; import any available metrics.')
        elif status == "Published":
            latest = sorted(perf_by_content[row["content_id"]], key=lambda item: item["observed_date"])[-1]
            known = next(((metric, latest[metric]) for metric in METRICS if latest[metric]), None)
            if known:
                actions.append(f'Review {known[0]} {fmt_number(known[1])} for “{title}” before deciding whether to reuse the theme.')
        if len(actions) >= 6:
            break
    return actions or ["No immediate action is supported by the current records. Add a confirmed status or result update when available."]


CSS = '''<style>:root{--ink:#26342f;--heading:#173e36;--muted:#6f746b;--line:#d9d3c5;--bg:#f3efe5;--card:#fffdf8;--accent:#a6533a;--green:#356a57;--blue:#577f91;--amber:#8a5a16}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 Inter,"Avenir Next","Helvetica Neue",Arial,sans-serif}main{max-width:1180px;margin:auto;padding:42px 24px 76px}header{padding-bottom:24px;border-bottom:1px solid var(--line);margin-bottom:24px}h1,h2{font-family:Georgia,"Times New Roman",serif;color:var(--heading)}h1{font-size:clamp(36px,6vw,58px);line-height:1.05;margin:8px 0 12px}h2{font-size:25px;margin:0 0 15px}p{max-width:820px}.eyebrow{font-size:12px;text-transform:uppercase;letter-spacing:.12em;font-weight:800;color:var(--accent)}.lead{font-size:18px;color:#4f5e58}.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:16px;margin:18px 0 28px}.card{grid-column:span 4;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px;box-shadow:0 6px 20px #493b2908}.quarter{grid-column:span 3}.half{grid-column:span 6}.wide{grid-column:span 12}.metric{font:700 34px Georgia,serif;color:var(--heading);margin:4px 0}.label,.muted{color:var(--muted)}.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:10px;background:var(--card)}table{border-collapse:collapse;width:100%;min-width:760px}th,td{padding:11px 12px;text-align:left;vertical-align:top;border-bottom:1px solid var(--line)}th{background:#e9ece5;color:#29463d;font-size:12px;text-transform:uppercase;letter-spacing:.05em}tr:last-child td{border-bottom:0}.record-id{display:block;color:var(--muted);font-size:11px;margin-top:3px}.badge{display:inline-block;border-radius:999px;padding:3px 8px;font-size:12px;font-weight:700;background:#ece9e2}.badge.good{background:#dce9df;color:#24533f}.badge.warn{background:#f3e3c8;color:#7a5012}.empty{border:1px dashed #b8b1a6;border-radius:10px;padding:24px;background:#fbf9f4;color:var(--muted)}.chart-layout{display:grid;grid-template-columns:minmax(200px,.8fr) minmax(230px,1.2fr);gap:22px;align-items:center}.donut-wrap{max-width:240px;margin:auto}.donut{width:100%;height:auto}.chart-value{font:700 28px Georgia,serif;fill:var(--ink)}.chart-label{font-size:11px;fill:var(--muted);text-transform:uppercase}.legend{display:grid;gap:9px}.legend-item{display:flex;gap:9px;align-items:flex-start}.legend-item small{display:block;color:var(--muted)}.swatch{width:11px;height:11px;border-radius:3px;margin-top:5px;flex:0 0 auto}.bar-chart{display:grid;gap:14px}.bar-heading{display:flex;justify-content:space-between;gap:12px}.bar-track{height:10px;background:#ebe5dc;border-radius:99px;overflow:hidden}.bar-track i{display:block;height:100%;border-radius:99px}.actions{padding-left:21px}.actions li{margin:8px 0}.path{font-family:ui-monospace,SFMono-Regular,monospace;background:#ece8df;border-radius:5px;padding:2px 5px}footer{margin-top:42px;border-top:1px solid var(--line);padding-top:18px;color:var(--muted);font-size:12px}@media(max-width:880px){.quarter{grid-column:span 6}.half{grid-column:span 12}}@media(max-width:640px){main{padding:26px 14px 54px}.card,.quarter,.half,.wide{grid-column:span 12}.chart-layout{grid-template-columns:1fr}table{min-width:680px}}</style>'''


def render_dashboard(workspace, today=None):
    workspace = Path(workspace)
    errors, calendar, performance = validate_workspace(workspace)
    if errors:
        raise ValueError("; ".join(errors))
    today = today or date.today()
    to_make = sum(row["status"] in {"Idea", "Planned", "Drafting"} for row in calendar)
    published = sum(row["status"] == "Published" for row in calendar)
    due = 0
    for row in calendar:
        if row["planned_date"] and row["status"] not in {"Published", "Cancelled"}:
            planned = date.fromisoformat(row["planned_date"])
            if today <= planned <= today + timedelta(days=7):
                due += 1
    overview = ''.join([
        f'<section class="card quarter"><div class="label">All content</div><div class="metric">{len(calendar)}</div><div class="muted">Saved platform versions</div></section>',
        f'<section class="card quarter"><div class="label">To make</div><div class="metric">{to_make}</div><div class="muted">Idea, planned or drafting</div></section>',
        f'<section class="card quarter"><div class="label">Published</div><div class="metric">{published}</div><div class="muted">Explicitly confirmed</div></section>',
        f'<section class="card quarter"><div class="label">Next 7 days</div><div class="metric">{due}</div><div class="muted">Recorded upcoming work</div></section>',
    ])
    upcoming = [row for row in calendar if row["status"] not in {"Published", "Cancelled"}]
    upcoming.sort(key=lambda row: (row["planned_date"] or "9999-99-99", row["title"], row["platform"]))
    if upcoming:
        body_rows = ''.join(f'<tr><td><b>{escape(row["title"])}</b><span class="record-id">Internal content ID: {escape(row["content_id"])}</span></td><td>{escape(row["platform"])}</td><td>{escape(row["planned_date"] or "Not scheduled")}</td><td>{badge(row["status"])}</td><td>{escape(row["draft_path"] or "Not created")}</td></tr>' for row in upcoming)
        calendar_html = f'<div class="table-wrap"><table><thead><tr><th>Content</th><th>Platform</th><th>Planned date</th><th>Status</th><th>Draft</th></tr></thead><tbody>{body_rows}</tbody></table></div>'
    else:
        calendar_html = empty("No upcoming content yet. Describe a goal or attach local materials to create the first plan.")
    status_chart = donut(Counter(row["status"] for row in calendar))
    platform_chart = bars(Counter(row["platform"] for row in calendar))
    titles = {row["content_id"]: row for row in calendar}
    if performance:
        perf_rows = []
        for row in sorted(performance, key=lambda item: (item["observed_date"], titles[item["content_id"]]["title"]), reverse=True):
            content = titles[row["content_id"]]
            metrics = ''.join(f'<td>{fmt_number(row[metric])}</td>' for metric in METRICS)
            perf_rows.append(f'<tr><td><b>{escape(content["title"])}</b><span class="record-id">Internal performance ID: {escape(row["performance_id"])}</span></td><td>{escape(row["platform"])}</td><td>{escape(row["observed_date"])}</td><td>{escape(row["metric_basis"] or "Not specified")}</td>{metrics}<td>{escape(row["source_reference"] or "Not recorded")}</td></tr>')
        metric_headers = ''.join(f'<th>{escape(metric.title())}</th>' for metric in METRICS)
        performance_html = f'<div class="table-wrap"><table><thead><tr><th>Content</th><th>Platform</th><th>Observed</th><th>Basis</th>{metric_headers}<th>Source</th></tr></thead><tbody>{"".join(perf_rows)}</tbody></table></div><p class="muted">Metrics retain their original platform meaning. Cumulative snapshots are shown by date and are not added together.</p>'
    else:
        performance_html = empty("No performance data yet. Published content remains visible while results are unavailable.")
    actions_html = ''.join(f'<li>{escape(action)}</li>' for action in next_actions(calendar, performance))
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Content Operations Workspace</title>{CSS}</head><body><main><header><div class="eyebrow">Plan · Create · Publish · Review</div><h1>Content Operations Workspace</h1><p class="lead">A local workspace for planning content, maintaining drafts, tracking confirmed publishing and learning from recorded results.</p></header><div class="grid">{overview}</div><section class="grid"><div class="card wide"><h2>Content Calendar / Upcoming</h2>{calendar_html}</div></section><section class="grid"><div class="card half"><h2>Status breakdown</h2>{status_chart}</div><div class="card half"><h2>Platform breakdown</h2>{platform_chart}</div></section><section class="grid"><div class="card wide"><h2>Performance Review</h2>{performance_html}</div></section><section class="grid"><div class="card wide"><h2>Next Actions</h2><ol class="actions">{actions_html}</ol></div></section><p class="muted">Source of truth: <span class="path">workspace/content-calendar.csv</span>, <span class="path">workspace/performance.csv</span> and Markdown drafts. Complete key actions through Agent conversation; preview links are not required.</p><footer>Content Operations Workspace · Generated from local workspace files</footer></main></body></html>\n'''

