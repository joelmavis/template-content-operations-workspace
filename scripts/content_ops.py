#!/usr/bin/env python3
"""Shared data contracts and HTML rendering for Content Operations Workspace."""
from __future__ import annotations

import csv
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from html import escape
import json
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
STATUS_ORDER = ["Idea", "Planned", "Drafting", "Ready", "Scheduled", "Published", "Paused", "Cancelled"]
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
    cls = (
        "good" if value == "Published"
        else "warn" if value in {"Ready", "Scheduled"}
        else "active" if value == "Drafting"
        else "neutral"
    )
    return f'<span class="badge {cls}">{escape(value)}</span>'


def timing_pill(planned_date, status, today):
    if status in {"Published", "Cancelled"} or not planned_date:
        return ""
    planned = date.fromisoformat(planned_date)
    if planned < today:
        return '<span class="time-pill overdue">Overdue</span>'
    if planned == today:
        return '<span class="time-pill today">Today</span>'
    if planned <= today + timedelta(days=7):
        return '<span class="time-pill soon">Next 7d</span>'
    return ""


def empty(message, hint=None):
    hint_html = f'<p class="empty-hint">{escape(hint)}</p>' if hint else ""
    return f'<div class="empty"><div class="empty-dot"></div><div><div class="empty-msg">{escape(message)}</div>{hint_html}</div></div>'


def pipeline_capsules(counts):
    total = sum(counts.values())
    if not total:
        return empty(
            "No content records yet, so no status distribution is shown.",
            "Describe a goal or attach local materials in Agent chat to populate the pipeline.",
        )
    active_statuses = [status for status in STATUS_ORDER if counts.get(status, 0) > 0]
    for status in sorted(counts):
        if status not in active_statuses:
            active_statuses.append(status)
    maximum = max(counts.values()) or 1
    bars_html = []
    for status in active_statuses:
        count = counts[status]
        height_pct = max(16, round(100 * count / maximum))
        share_pct = round(100 * count / total)
        bars_html.append(
            f'<div class="capsule-col" title="{escape(status)}: {count} ({share_pct}%)">'
            f'<span class="capsule-val">{count}</span>'
            f'<div class="capsule-track"><div class="capsule-fill" style="height:{height_pct}%"></div></div>'
            f'<span class="capsule-lbl">{escape(status)}</span>'
            f'</div>'
        )
    return f'<div class="capsule-chart">{"".join(bars_html)}</div>'


def platform_bars(counts):
    total = sum(counts.values())
    if not total:
        return empty(
            "No content records yet, so no platform distribution is shown.",
            "Add your first cross-platform plan via Agent chat.",
        )
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    rows = []
    for label, count in ordered:
        pct = round(100 * count / total)
        rows.append(
            f'<div class="dark-bar-row">'
            f'<div class="dark-bar-head"><span>{escape(label)}</span><b>{count} · {pct}%</b></div>'
            f'<div class="dark-bar-track"><i style="width:{max(6, pct)}%"></i></div>'
            f'</div>'
        )
    return f'<div class="dark-bars">{"".join(rows)}</div>'


def next_actions(calendar, performance):
    if not calendar:
        return [
            ("Describe a content goal or attach local materials to create the first plan.",
             "Create a 7-day X and Medium content plan for my product and update the workspace."),
        ]
    perf_by_content = {}
    for row in performance:
        perf_by_content.setdefault(row["content_id"], []).append(row)
    actions = []
    for row in sorted(calendar, key=lambda item: (item["planned_date"] or "9999-99-99", item["title"])):
        title = row["title"]
        platform = row["platform"]
        status = row["status"]
        if status in {"Idea", "Planned"}:
            actions.append((
                f'Draft “{title}” for {platform}.',
                f'Draft "{title}" for {platform} and link it in workspace/content-calendar.csv.',
            ))
        elif status == "Drafting":
            actions.append((
                f'Finish and review the {platform} draft “{title}”.',
                f'Review and polish the {platform} draft "{title}" and move it to Ready if complete.',
            ))
        elif status == "Ready":
            actions.append((
                f'Review “{title}” and decide whether to schedule it for {platform}.',
                f'Schedule "{title}" for {platform} and confirm the planned date.',
            ))
        elif status == "Scheduled":
            date_text = f' on {row["planned_date"]}' if row["planned_date"] else ""
            actions.append((
                f'Confirm whether “{title}” was actually published to {platform}{date_text}; do not advance it automatically.',
                f'Record that "{title}" on {platform} was published today.',
            ))
        elif status == "Published" and not perf_by_content.get(row["content_id"]):
            actions.append((
                f'“{title}” is published on {platform} but has no recorded results; import any available metrics.',
                f'Import performance results for "{title}" on {platform}.',
            ))
        elif status == "Published":
            latest = sorted(perf_by_content[row["content_id"]], key=lambda item: item["observed_date"])[-1]
            known = next(((metric, latest[metric]) for metric in METRICS if latest[metric]), None)
            if known:
                actions.append((
                    f'Review {known[0]} {fmt_number(known[1])} for “{title}” before deciding whether to reuse the theme.',
                    f'Review performance for "{title}" on {platform} and recommend what to repeat next week.',
                ))
        if len(actions) >= 6:
            break
    return actions or [(
        "No immediate action is supported by the current records. Add a confirmed status or result update when available.",
        "Review my current content calendar and suggest what I should work on today.",
    )]


def read_brand_name(workspace):
    brand_path = Path(workspace) / "brand-context.md"
    if not brand_path.is_file():
        return "Local Workspace"
    for line in brand_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("- Brand or project:") and ":" in line:
            val = line.split(":", 1)[1].strip()
            if val:
                return val
    return "Local Workspace"


CSS = '''<style>
:root{
  --bg-1:#f6e8de;
  --bg-2:#ebd4c4;
  --bg-3:#e2c6b4;
  --shell:rgba(255,250,246,.46);
  --shell-border:rgba(255,255,255,.72);
  --sidebar:rgba(255,251,248,.58);
  --glass:rgba(255,255,255,.62);
  --glass-strong:rgba(255,255,255,.88);
  --glass-border:rgba(255,255,255,.78);
  --ink:#241914;
  --ink-soft:#5b4a42;
  --muted:#877368;
  --accent:#c67647;
  --accent-2:#df9866;
  --accent-soft:rgba(198,118,71,.14);
  --rose:#c9868c;
  --good-bg:rgba(46,125,91,.13);
  --good-ink:#1f6145;
  --warn-bg:rgba(198,118,71,.16);
  --warn-ink:#9a4d22;
  --danger-bg:rgba(196,69,69,.14);
  --danger-ink:#9d2d2d;
  --dark-1:#2a1f19;
  --dark-2:#14100e;
  --radius-xl:28px;
  --radius-lg:22px;
  --radius-md:16px;
  --shadow-shell:0 28px 70px rgba(102,65,42,.14),0 2px 8px rgba(102,65,42,.06);
  --shadow-card:0 10px 28px rgba(114,74,48,.07);
  --shadow-pill:0 8px 22px rgba(124,78,48,.13),0 1px 3px rgba(124,78,48,.08);
  --font:-apple-system,BlinkMacSystemFont,"SF Pro Display","Inter","Segoe UI",Roboto,sans-serif;
  --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0;min-height:100%}
body{
  font:14px/1.55 var(--font);
  color:var(--ink);
  background:
    radial-gradient(900px 600px at 8% 6%, rgba(255,246,238,.9), transparent 60%),
    radial-gradient(760px 560px at 92% 18%, rgba(226,174,142,.42), transparent 62%),
    radial-gradient(720px 520px at 65% 95%, rgba(217,154,146,.28), transparent 62%),
    linear-gradient(135deg, var(--bg-1) 0%, var(--bg-2) 52%, var(--bg-3) 100%);
  padding:22px;
  -webkit-font-smoothing:antialiased;
}
.shell{
  max-width:1320px;
  margin:0 auto;
  display:grid;
  grid-template-columns:224px minmax(0,1fr);
  gap:20px;
  padding:18px;
  border-radius:var(--radius-xl);
  background:var(--shell);
  backdrop-filter:blur(26px);
  -webkit-backdrop-filter:blur(26px);
  border:1px solid var(--shell-border);
  box-shadow:var(--shadow-shell);
  min-height:calc(100vh - 44px);
}
/* Sidebar & 01 Liquid Pill */
.sidebar{
  display:flex;
  flex-direction:column;
  justify-content:space-between;
  padding:18px 12px 14px;
  border-radius:var(--radius-lg);
  background:var(--sidebar);
  border:1px solid rgba(255,255,255,.72);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.8);
}
.brand{
  display:flex;
  align-items:center;
  gap:11px;
  padding:4px 10px 20px;
}
.brand-mark{
  width:34px;
  height:34px;
  border-radius:11px;
  background:linear-gradient(135deg,#e39b67 0%,#b8653b 100%);
  box-shadow:0 6px 14px rgba(184,101,59,.32),inset 0 1px 1px rgba(255,255,255,.55);
  display:grid;
  place-items:center;
  color:#fff;
  font-weight:800;
  font-size:14px;
  flex:0 0 auto;
}
.brand-name{font-size:15px;font-weight:700;letter-spacing:-.02em;line-height:1.2}
.brand-sub{font-size:11px;color:var(--muted)}
.nav-wrap{position:relative;display:flex;flex-direction:column;gap:4px}
.nav-pill{
  position:absolute;
  left:0;
  right:0;
  height:42px;
  border-radius:999px;
  background:rgba(255,255,255,.94);
  border:1px solid rgba(255,255,255,.98);
  box-shadow:var(--shadow-pill);
  pointer-events:none;
  transition:transform .46s cubic-bezier(.34,1.38,.64,1),height .3s ease,opacity .25s ease;
  z-index:0;
}
.nav-item{
  position:relative;
  z-index:1;
  display:flex;
  align-items:center;
  gap:10px;
  height:42px;
  padding:0 14px;
  border:0;
  background:transparent;
  color:var(--ink-soft);
  font:500 13.5px var(--font);
  border-radius:999px;
  cursor:pointer;
  text-align:left;
  transition:color .2s ease;
}
.nav-item:hover{color:var(--ink)}
.nav-item.active{color:var(--ink);font-weight:650}
.nav-item svg{width:16px;height:16px;stroke:currentColor;fill:none;stroke-width:1.8;flex:0 0 auto;opacity:.82}
.nav-item.active svg{opacity:1;stroke:var(--accent)}
.nav-count{
  margin-left:auto;
  font-size:11px;
  font-weight:650;
  color:var(--muted);
  background:rgba(135,115,104,.11);
  padding:2px 7px;
  border-radius:999px;
}
.nav-item.active .nav-count{background:var(--accent-soft);color:var(--accent)}
.sidebar-foot{
  margin-top:20px;
  padding:12px;
  border-radius:16px;
  background:rgba(255,255,255,.68);
  border:1px solid rgba(255,255,255,.84);
  display:flex;
  align-items:center;
  gap:10px;
}
.avatar{
  width:34px;
  height:34px;
  border-radius:999px;
  background:linear-gradient(135deg,#d88a59,#b9673c);
  color:#fff;
  font-weight:700;
  font-size:12px;
  display:grid;
  place-items:center;
  flex:0 0 auto;
}
.foot-title{font-size:12.5px;font-weight:650;line-height:1.25;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.foot-sub{font-size:11px;color:var(--muted)}
/* Main Column & Topbar */
.main{display:flex;flex-direction:column;gap:16px;min-width:0;padding:4px 4px 8px}
.topbar{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:14px;
  flex-wrap:wrap;
  padding:4px 4px 2px;
}
.title-block h1{
  margin:0;
  font-size:clamp(22px,2.4vw,28px);
  font-weight:750;
  letter-spacing:-.03em;
  line-height:1.15;
}
.title-sub{margin:3px 0 0;font-size:12.5px;color:var(--muted)}
.toolbar{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
/* 04 Liquid Split Filter */
.split-wrap{
  display:inline-flex;
  align-items:center;
  gap:6px;
  padding:4px;
  border-radius:999px;
  background:rgba(255,255,255,.58);
  border:1px solid rgba(255,255,255,.82);
  box-shadow:0 4px 14px rgba(114,74,48,.07);
  transition:all .38s cubic-bezier(.34,1.35,.64,1);
}
.split-trigger,.split-chip,.pill-btn,.icon-btn{
  border:0;
  font:550 12.5px var(--font);
  cursor:pointer;
  transition:all .26s cubic-bezier(.34,1.35,.64,1);
}
.split-trigger{
  display:inline-flex;
  align-items:center;
  gap:6px;
  padding:7px 14px;
  border-radius:999px;
  background:#fff;
  color:var(--ink);
  box-shadow:0 3px 10px rgba(114,74,48,.09);
}
.split-trigger:hover{transform:translateY(-1px)}
.split-chips{
  display:flex;
  align-items:center;
  gap:4px;
  max-width:0;
  opacity:0;
  overflow:hidden;
  transition:max-width .45s cubic-bezier(.22,1,.36,1),opacity .28s ease;
}
.split-wrap.open .split-chips{max-width:520px;opacity:1;padding-right:4px}
.split-chip{
  padding:6px 11px;
  border-radius:999px;
  background:rgba(255,255,255,.72);
  color:var(--ink-soft);
  white-space:nowrap;
  transform:scale(.85);
}
.split-wrap.open .split-chip{transform:scale(1)}
.split-chip:hover{background:#fff;color:var(--ink)}
.split-chip.active{background:var(--accent);color:#fff;box-shadow:0 4px 12px rgba(198,118,71,.32)}
.pill-btn{
  display:inline-flex;
  align-items:center;
  gap:6px;
  padding:8px 14px;
  border-radius:999px;
  background:rgba(255,255,255,.72);
  border:1px solid rgba(255,255,255,.85);
  color:var(--ink-soft);
  box-shadow:0 4px 12px rgba(114,74,48,.06);
}
.pill-btn:hover{background:#fff;color:var(--ink);transform:translateY(-1px)}
.pill-btn.active{
  background:linear-gradient(135deg,#2a1f19,#15110f);
  color:#fff;
  border-color:rgba(255,255,255,.15);
  box-shadow:0 8px 20px rgba(36,25,20,.24);
}
.icon-btn{
  width:38px;
  height:38px;
  border-radius:999px;
  display:grid;
  place-items:center;
  background:rgba(255,255,255,.78);
  border:1px solid rgba(255,255,255,.88);
  color:var(--ink-soft);
  box-shadow:0 4px 12px rgba(114,74,48,.06);
}
.icon-btn svg{width:17px;height:17px;stroke:currentColor;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.icon-btn:hover{background:#fff;color:var(--ink);transform:translateY(-1px)}
.search-box{
  display:none;
  align-items:center;
  background:rgba(255,255,255,.88);
  border:1px solid rgba(255,255,255,.95);
  border-radius:999px;
  padding:0 14px;
  height:38px;
}
.search-box.open{display:inline-flex}
.search-box input{
  border:0;
  outline:0;
  background:transparent;
  font:13px var(--font);
  color:var(--ink);
  width:165px;
}
/* Bento Grid & 02 Light Follow + 3D Tilt */
.bento{
  display:grid;
  grid-template-columns:repeat(12,minmax(0,1fr));
  gap:16px;
  align-items:stretch;
}
.card{
  position:relative;
  border-radius:var(--radius-lg);
  background:var(--glass);
  backdrop-filter:blur(20px);
  -webkit-backdrop-filter:blur(20px);
  border:1px solid var(--glass-border);
  box-shadow:var(--shadow-card);
  padding:20px;
  overflow:hidden;
  transform-style:preserve-3d;
  transition:transform .28s cubic-bezier(.22,1,.36,1),box-shadow .28s ease,opacity .25s ease;
  --mx:50%;
  --my:50%;
}
.card::before{
  content:"";
  position:absolute;
  inset:0;
  border-radius:inherit;
  background:radial-gradient(300px circle at var(--mx) var(--my), rgba(255,255,255,.58), transparent 64%);
  opacity:0;
  pointer-events:none;
  transition:opacity .28s ease;
  z-index:0;
}
.card::after{
  content:"";
  position:absolute;
  inset:0;
  border-radius:inherit;
  padding:1.25px;
  background:radial-gradient(220px circle at var(--mx) var(--my), rgba(255,255,255,.98), rgba(223,152,102,.32) 45%, transparent 72%);
  -webkit-mask:linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite:xor;
  mask-composite:exclude;
  opacity:0;
  pointer-events:none;
  transition:opacity .28s ease;
  z-index:2;
}
.card:hover::before,.card:hover::after{opacity:1}
.card:hover{box-shadow:0 18px 40px rgba(114,74,48,.12)}
.card > *{position:relative;z-index:1}
/* Dark Accent Card (Reference: Working Format) */
.card-dark{
  background:
    radial-gradient(240px circle at 92% 8%, rgba(223,152,102,.28), transparent 62%),
    linear-gradient(155deg, var(--dark-1) 0%, var(--dark-2) 78%);
  border:1px solid rgba(255,220,196,.14);
  color:#faf3ee;
  box-shadow:0 18px 42px rgba(24,15,10,.26);
}
.card-dark::before{
  background:radial-gradient(280px circle at var(--mx) var(--my), rgba(235,168,120,.18), transparent 64%);
}
.card-dark::after{
  background:radial-gradient(220px circle at var(--mx) var(--my), rgba(240,180,136,.65), transparent 70%);
}
.card-dark .card-title{color:#faf3ee}
.card-dark .card-sub,.card-dark .muted{color:rgba(250,243,238,.6)}
.card-dark .empty{background:rgba(255,255,255,.05);border-color:rgba(255,255,255,.15);color:rgba(250,243,238,.72)}
.card-dark .expand-btn{background:rgba(255,255,255,.1);color:#fff;border-color:rgba(255,255,255,.16)}
.card-dark .expand-btn:hover{background:rgba(255,255,255,.2)}
/* Spans */
.span-3{grid-column:span 3}
.span-4{grid-column:span 4}
.span-5{grid-column:span 5}
.span-7{grid-column:span 7}
.span-8{grid-column:span 8}
.span-12{grid-column:span 12}
/* KPI Cards */
.kpi-label{font-size:12.5px;color:var(--muted);font-weight:550}
.kpi-row{display:flex;align-items:flex-end;justify-content:space-between;gap:10px;margin-top:8px}
.kpi-val{font-size:32px;font-weight:760;letter-spacing:-.04em;line-height:1.05;font-variant-numeric:tabular-nums}
.kpi-foot{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:12px}
.kpi-pill{
  display:inline-flex;
  align-items:center;
  padding:3px 9px;
  border-radius:999px;
  font-size:11px;
  font-weight:650;
  background:linear-gradient(135deg,#cf7d4d,#b9663a);
  color:#fff;
  white-space:nowrap;
}
.kpi-pill.soft{background:rgba(135,115,104,.13);color:var(--ink-soft)}
.spark{width:68px;height:22px;overflow:visible}
.spark path{fill:none;stroke:var(--accent);stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
/* Card Header + 03 Expand in Place */
.card-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:14px}
.card-title{margin:0;font-size:16px;font-weight:700;letter-spacing:-.02em}
.card-sub{margin:2px 0 0;font-size:12px;color:var(--muted)}
.card-head-right{display:flex;align-items:center;gap:8px;flex-shrink:0}
.big-stat{font-size:26px;font-weight:760;letter-spacing:-.03em;font-variant-numeric:tabular-nums}
.expand-btn{
  width:30px;
  height:30px;
  border-radius:999px;
  border:1px solid rgba(135,115,104,.18);
  background:rgba(255,255,255,.78);
  color:var(--ink-soft);
  display:grid;
  place-items:center;
  cursor:pointer;
  font-size:13px;
  transition:all .2s ease;
}
.expand-btn:hover{background:#fff;color:var(--ink);transform:scale(1.06)}
/* Expanded Mode (03 Expand in Place) */
.bento.has-expanded .card:not(.is-expanded){
  grid-column:span 3;
  padding:14px;
  cursor:pointer;
  opacity:.86;
  max-height:132px;
}
.bento.has-expanded .card:not(.is-expanded) .hide-mini{display:none}
.bento.has-expanded .card:not(.is-expanded):hover{opacity:1;transform:translateY(-2px)}
.bento.has-expanded .card.is-expanded{
  grid-column:1 / -1;
  order:-1;
  padding:26px;
  box-shadow:0 24px 60px rgba(102,65,42,.16);
}
.bento.has-expanded .card.is-expanded .capsule-chart{height:270px}
/* Pipeline Capsule Chart */
.capsule-chart{
  display:flex;
  align-items:flex-end;
  justify-content:space-between;
  gap:12px;
  height:188px;
  padding:10px 6px 2px;
  transition:height .35s ease;
}
.capsule-col{
  flex:1;
  height:100%;
  display:flex;
  flex-direction:column;
  align-items:center;
  gap:8px;
  min-width:34px;
}
.capsule-val{font-size:11.5px;font-weight:700;color:var(--ink-soft);font-variant-numeric:tabular-nums}
.capsule-track{
  width:100%;
  max-width:26px;
  flex:1;
  border-radius:999px;
  background:rgba(255,255,255,.65);
  border:1px solid rgba(255,255,255,.85);
  display:flex;
  align-items:flex-end;
  overflow:hidden;
  padding:2px;
}
.capsule-fill{
  width:100%;
  border-radius:999px;
  background:linear-gradient(180deg,#e49b65 0%,#cc868b 100%);
  box-shadow:0 4px 12px rgba(204,134,139,.28);
  transition:height .55s cubic-bezier(.22,1,.36,1);
}
.capsule-lbl{
  font-size:11px;
  color:var(--muted);
  font-weight:550;
  white-space:nowrap;
  overflow:hidden;
  text-overflow:ellipsis;
  max-width:68px;
}
/* Dark Platform Bars */
.dark-hero-num{font-size:34px;font-weight:760;letter-spacing:-.04em;line-height:1.05;margin:4px 0 2px}
.dark-bars{display:flex;flex-direction:column;gap:14px;margin-top:16px}
.dark-bar-head{display:flex;justify-content:space-between;font-size:12.5px;margin-bottom:6px}
.dark-bar-head span{color:rgba(250,243,238,.86)}
.dark-bar-head b{color:#fff;font-weight:650;font-variant-numeric:tabular-nums}
.dark-bar-track{height:8px;border-radius:999px;background:rgba(255,255,255,.11);overflow:hidden}
.dark-bar-track i{
  display:block;
  height:100%;
  border-radius:999px;
  background:linear-gradient(90deg,#e39b67 0%,#f1be8b 100%);
  transition:width .55s cubic-bezier(.22,1,.36,1);
}
/* Tables & Badges */
.view-switch{
  display:inline-flex;
  padding:3px;
  border-radius:999px;
  background:rgba(135,115,104,.11);
}
.view-tab{
  border:0;
  background:transparent;
  padding:4px 10px;
  border-radius:999px;
  font:600 11.5px var(--font);
  color:var(--ink-soft);
  cursor:pointer;
}
.view-tab.active{background:#fff;color:var(--ink);box-shadow:0 2px 6px rgba(102,65,42,.1)}
.table-wrap{
  overflow:auto;
  border-radius:14px;
  border:1px solid rgba(135,115,104,.15);
  background:rgba(255,255,255,.68);
}
table{border-collapse:collapse;width:100%;min-width:680px}
th,td{padding:11px 13px;text-align:left;vertical-align:top;border-bottom:1px solid rgba(135,115,104,.12);font-size:13px}
th{
  background:rgba(244,234,225,.75);
  color:var(--ink-soft);
  font-size:11px;
  font-weight:700;
  text-transform:uppercase;
  letter-spacing:.05em;
  white-space:nowrap;
}
tr:last-child td{border-bottom:0}
tbody tr:hover td{background:rgba(255,255,255,.62)}
.record-id{display:block;color:var(--muted);font-size:11px;margin-top:2px;font-family:var(--mono)}
.badge{
  display:inline-flex;
  align-items:center;
  gap:5px;
  border-radius:999px;
  padding:3px 9px;
  font-size:11.5px;
  font-weight:650;
  background:rgba(135,115,104,.13);
  color:var(--ink-soft);
  white-space:nowrap;
}
.badge.good{background:var(--good-bg);color:var(--good-ink)}
.badge.warn{background:var(--warn-bg);color:var(--warn-ink)}
.badge.active{background:rgba(198,118,71,.2);color:#91461d}
.time-pill{
  display:inline-block;
  margin-left:6px;
  padding:2px 7px;
  border-radius:999px;
  font-size:10.5px;
  font-weight:700;
}
.time-pill.overdue{background:var(--danger-bg);color:var(--danger-ink)}
.time-pill.today{background:var(--warn-bg);color:var(--warn-ink)}
.time-pill.soon{background:var(--good-bg);color:var(--good-ink)}
/* Kanban View */
.kanban{display:none;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}
.kanban.show{display:grid}
.kanban-col{
  background:rgba(255,255,255,.52);
  border:1px solid rgba(255,255,255,.8);
  border-radius:16px;
  padding:12px;
  display:flex;
  flex-direction:column;
  gap:8px;
}
.kanban-head{display:flex;justify-content:space-between;align-items:center;font-size:12px;font-weight:700;color:var(--ink-soft);margin-bottom:4px}
.kanban-item{
  background:#fff;
  border-radius:12px;
  padding:10px 11px;
  border:1px solid rgba(135,115,104,.12);
  box-shadow:0 3px 10px rgba(102,65,42,.05);
}
.kanban-item b{display:block;font-size:12.5px;margin-bottom:4px}
.kanban-meta{font-size:11px;color:var(--muted);display:flex;justify-content:space-between;gap:6px}
/* Next Actions List */
.actions-list{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:9px}
.action-row{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:12px;
  padding:11px 14px;
  border-radius:14px;
  background:rgba(255,255,255,.76);
  border:1px solid rgba(255,255,255,.92);
}
.action-left{display:flex;align-items:flex-start;gap:10px;min-width:0}
.action-idx{
  width:24px;
  height:24px;
  border-radius:999px;
  background:var(--accent-soft);
  color:var(--accent);
  font-size:11.5px;
  font-weight:750;
  display:grid;
  place-items:center;
  flex:0 0 auto;
}
.action-text{font-size:13px;color:var(--ink);line-height:1.45}
.copy-btn{
  border:1px solid rgba(198,118,71,.24);
  background:#fff;
  color:var(--accent);
  border-radius:999px;
  padding:5px 11px;
  font:600 11.5px var(--font);
  cursor:pointer;
  white-space:nowrap;
  flex:0 0 auto;
  transition:all .2s ease;
}
.copy-btn:hover{background:var(--accent);color:#fff}
/* Empty State */
.empty{
  display:flex;
  align-items:flex-start;
  gap:12px;
  border:1px dashed rgba(154,126,110,.38);
  border-radius:16px;
  padding:20px;
  background:rgba(255,255,255,.46);
  color:var(--ink-soft);
}
.empty-dot{
  width:10px;
  height:10px;
  border-radius:999px;
  background:linear-gradient(135deg,#e09664,#c9868c);
  margin-top:6px;
  flex:0 0 auto;
}
.empty-msg{font-weight:600;font-size:13.5px}
.empty-hint{margin:4px 0 0;font-size:12px;color:var(--muted)}
.path{font-family:var(--mono);font-size:12px;background:rgba(255,255,255,.72);border:1px solid rgba(135,115,104,.16);border-radius:6px;padding:2px 6px}
.muted{color:var(--muted);font-size:12px}
.foot-note{
  display:flex;
  justify-content:space-between;
  align-items:center;
  flex-wrap:wrap;
  gap:8px;
  padding:6px 6px 0;
  font-size:12px;
  color:var(--muted);
}
.toast{
  position:fixed;
  right:26px;
  bottom:26px;
  background:#241914;
  color:#faf3ee;
  padding:10px 16px;
  border-radius:999px;
  font-size:12.5px;
  font-weight:600;
  box-shadow:0 12px 30px rgba(36,25,20,.28);
  opacity:0;
  transform:translateY(10px);
  pointer-events:none;
  transition:all .25s ease;
  z-index:99;
}
.toast.show{opacity:1;transform:translateY(0)}
.hidden-sec{display:none !important}
@media(max-width:980px){
  .shell{grid-template-columns:1fr;padding:14px}
  .sidebar{flex-direction:row;align-items:center;flex-wrap:wrap;padding:12px}
  .brand{padding:0 8px 0 0}
  .nav-wrap{flex-direction:row;flex-wrap:wrap}
  .nav-pill{display:none}
  .nav-item.active{background:#fff;box-shadow:var(--shadow-pill)}
  .sidebar-foot{display:none}
  .span-3{grid-column:span 6}
  .span-5,.span-7,.span-4,.span-8{grid-column:span 12}
}
@media(max-width:620px){
  body{padding:10px}
  .span-3{grid-column:span 12}
  .action-row{flex-direction:column;align-items:flex-start}
}
</style>'''


JS = '''<script>
(() => {
  const navWrap = document.getElementById('nav-wrap');
  const navPill = document.getElementById('nav-pill');
  const navItems = Array.from(document.querySelectorAll('.nav-item'));
  const bento = document.getElementById('bento');
  const cards = Array.from(document.querySelectorAll('.card[data-tilt]'));
  const splitWrap = document.getElementById('split-wrap');
  const splitTrigger = document.getElementById('split-trigger');
  const splitLabel = document.getElementById('split-label');
  const searchToggle = document.getElementById('search-toggle');
  const searchBox = document.getElementById('search-box');
  const searchInput = document.getElementById('search-input');
  const toast = document.getElementById('toast');

  let activeSection = 'overview';
  let activePlatform = 'ALL';
  let searchQuery = '';

  function showToast(msg) {
    toast.textContent = msg;
    toast.classList.add('show');
    clearTimeout(showToast._t);
    showToast._t = setTimeout(() => toast.classList.remove('show'), 2200);
  }

  /* 01 Liquid Pill Navigation */
  function positionPill(btn) {
    if (!navPill || !btn) return;
    navPill.style.transform = `translateY(${btn.offsetTop}px)`;
    navPill.style.height = `${btn.offsetHeight}px`;
  }

  function setSection(section) {
    activeSection = section;
    clearExpand();
    navItems.forEach((btn) => {
      const on = btn.dataset.section === section;
      btn.classList.toggle('active', on);
      if (on) positionPill(btn);
    });
    document.querySelectorAll('[data-groups]').forEach((el) => {
      const groups = (el.dataset.groups || '').split(' ');
      el.classList.toggle('hidden-sec', !groups.includes(section));
    });
  }

  navItems.forEach((btn) => btn.addEventListener('click', () => setSection(btn.dataset.section)));
  window.addEventListener('resize', () => {
    const active = navItems.find((b) => b.classList.contains('active'));
    if (active) positionPill(active);
  });
  requestAnimationFrame(() => positionPill(navItems[0]));

  /* 02 Light Follow + Subtle 3D Tilt (<= 3.5deg) */
  cards.forEach((card) => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      card.style.setProperty('--mx', `${x}px`);
      card.style.setProperty('--my', `${y}px`);
      if (card.classList.contains('is-expanded')) {
        card.style.transform = '';
        return;
      }
      const nx = (x / rect.width - 0.5) * 2;
      const ny = (y / rect.height - 0.5) * 2;
      const rx = (-ny * 3.2).toFixed(2);
      const ry = (nx * 3.2).toFixed(2);
      card.style.transform = `perspective(920px) rotateX(${rx}deg) rotateY(${ry}deg) translateY(-2px)`;
    });
    card.addEventListener('mouseleave', () => {
      card.style.transform = '';
    });
  });

  /* 03 Expand in Place */
  function clearExpand() {
    bento.classList.remove('has-expanded');
    document.querySelectorAll('.card.is-expanded').forEach((c) => {
      c.classList.remove('is-expanded');
      const btn = c.querySelector('.expand-btn');
      if (btn) btn.textContent = '⤢';
    });
  }

  function toggleExpand(card) {
    const already = card.classList.contains('is-expanded');
    clearExpand();
    if (!already) {
      bento.classList.add('has-expanded');
      card.classList.add('is-expanded');
      card.style.transform = '';
      const btn = card.querySelector('.expand-btn');
      if (btn) btn.textContent = '×';
    }
  }

  document.querySelectorAll('.expand-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const card = btn.closest('.card');
      if (card) toggleExpand(card);
    });
  });

  document.querySelectorAll('.card[data-expandable]').forEach((card) => {
    card.addEventListener('click', () => {
      if (bento.classList.contains('has-expanded') && !card.classList.contains('is-expanded')) {
        toggleExpand(card);
      }
    });
  });

  /* 04 Liquid Split Platform Filter + Search */
  splitTrigger.addEventListener('click', () => splitWrap.classList.toggle('open'));

  function bindSplitChips() {
    document.querySelectorAll('.split-chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        activePlatform = chip.dataset.platform || 'ALL';
        document.querySelectorAll('.split-chip').forEach((c) => c.classList.toggle('active', c === chip));
        splitLabel.textContent = activePlatform === 'ALL' ? 'All Platforms' : activePlatform;
        applyFilters();
      });
    });
  }
  bindSplitChips();

  searchToggle.addEventListener('click', () => {
    searchBox.classList.toggle('open');
    if (searchBox.classList.contains('open')) searchInput.focus();
  });

  searchInput.addEventListener('input', (e) => {
    searchQuery = (e.target.value || '').trim().toLowerCase();
    applyFilters();
  });

  function applyFilters() {
    document.querySelectorAll('tr[data-platform], .kanban-item[data-platform]').forEach((node) => {
      const p = node.dataset.platform || '';
      const text = (node.textContent || '').toLowerCase();
      const matchPlatform = activePlatform === 'ALL' || p === activePlatform;
      const matchSearch = !searchQuery || text.includes(searchQuery);
      node.style.display = matchPlatform && matchSearch ? '' : 'none';
    });
  }

  /* Calendar Table / Kanban Toggle */
  document.querySelectorAll('.view-tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      const mode = tab.dataset.view;
      document.querySelectorAll('.view-tab').forEach((t) => t.classList.toggle('active', t === tab));
      document.getElementById('calendar-table-wrap').style.display = mode === 'table' ? '' : 'none';
      document.getElementById('calendar-kanban').classList.toggle('show', mode === 'kanban');
    });
  });

  /* Copy Prompt Buttons */
  function bindCopyButtons() {
    document.querySelectorAll('.copy-btn').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const prompt = btn.dataset.prompt || '';
        try {
          await navigator.clipboard.writeText(prompt);
          showToast('Prompt copied — paste into Agent chat');
        } catch {
          showToast(prompt);
        }
      });
    });
  }
  bindCopyButtons();
})();
</script>'''


def render_dashboard(workspace, today=None):
    workspace = Path(workspace)
    errors, calendar, performance = validate_workspace(workspace)
    if errors:
        raise ValueError("; ".join(errors))
    today = today or date.today()
    brand_name = read_brand_name(workspace)
    to_make = sum(row["status"] in {"Idea", "Planned", "Drafting"} for row in calendar)
    published = sum(row["status"] == "Published" for row in calendar)
    due = 0
    for row in calendar:
        if row["planned_date"] and row["status"] not in {"Published", "Cancelled"}:
            planned = date.fromisoformat(row["planned_date"])
            if today <= planned <= today + timedelta(days=7):
                due += 1
    pub_pct = f"{round(100 * published / len(calendar))}% Published" if calendar else "0% Published"

    platforms = sorted({row["platform"] for row in calendar})
    split_chips_html = '<button class="split-chip active" data-platform="ALL">All</button>' + ''.join(
        f'<button class="split-chip" data-platform="{escape(p)}">{escape(p)}</button>' for p in platforms
    )

    upcoming = [row for row in calendar if row["status"] not in {"Published", "Cancelled"}]
    upcoming.sort(key=lambda row: (row["planned_date"] or "9999-99-99", row["title"], row["platform"]))
    if upcoming:
        body_rows = ''.join(
            f'<tr data-platform="{escape(row["platform"])}">'
            f'<td><b>{escape(row["title"])}</b><span class="record-id">Internal content ID: {escape(row["content_id"])}</span></td>'
            f'<td>{escape(row["platform"])}</td>'
            f'<td>{escape(row["planned_date"] or "Not scheduled")}{timing_pill(row["planned_date"], row["status"], today)}</td>'
            f'<td>{badge(row["status"])}</td>'
            f'<td>{escape(row["draft_path"] or "Not created")}</td>'
            f'</tr>'
            for row in upcoming
        )
        calendar_html = (
            '<div class="table-wrap"><table>'
            '<thead><tr><th>Content</th><th>Platform</th><th>Planned date</th><th>Status</th><th>Draft</th></tr></thead>'
            f'<tbody>{body_rows}</tbody></table></div>'
        )
        kanban_groups = [
            ("Idea & Planned", [r for r in upcoming if r["status"] in {"Idea", "Planned"}]),
            ("Drafting", [r for r in upcoming if r["status"] == "Drafting"]),
            ("Ready & Scheduled", [r for r in upcoming if r["status"] in {"Ready", "Scheduled"}]),
        ]
        kanban_cols = []
        for col_name, items in kanban_groups:
            cards_html = ''.join(
                f'<div class="kanban-item" data-platform="{escape(r["platform"])}">'
                f'<b>{escape(r["title"])}</b>'
                f'<div class="kanban-meta"><span>{escape(r["platform"])}</span><span>{escape(r["planned_date"] or "Unscheduled")}</span></div>'
                f'</div>'
                for r in items
            ) or '<div class="muted">None</div>'
            kanban_cols.append(f'<div class="kanban-col"><div class="kanban-head"><span>{col_name}</span><span>{len(items)}</span></div>{cards_html}</div>')
        kanban_html = ''.join(kanban_cols)
    else:
        calendar_html = empty(
            "No upcoming content yet. Describe a goal or attach local materials to create the first plan.",
            "Send your first goal or attach a product brief in Agent chat to populate this calendar.",
        )
        kanban_html = calendar_html

    status_chart = pipeline_capsules(Counter(row["status"] for row in calendar))
    platform_chart = platform_bars(Counter(row["platform"] for row in calendar))
    titles = {row["content_id"]: row for row in calendar}

    if performance:
        perf_rows = []
        for row in sorted(performance, key=lambda item: (item["observed_date"], titles[item["content_id"]]["title"]), reverse=True):
            content = titles[row["content_id"]]
            metrics = ''.join(f'<td>{fmt_number(row[metric])}</td>' for metric in METRICS)
            perf_rows.append(
                f'<tr data-platform="{escape(row["platform"])}">'
                f'<td><b>{escape(content["title"])}</b><span class="record-id">Internal performance ID: {escape(row["performance_id"])}</span></td>'
                f'<td>{escape(row["platform"])}</td>'
                f'<td>{escape(row["observed_date"])}</td>'
                f'<td>{escape(row["metric_basis"] or "Not specified")}</td>'
                f'{metrics}'
                f'<td>{escape(row["source_reference"] or "Not recorded")}</td>'
                f'</tr>'
            )
        metric_headers = ''.join(f'<th>{escape(metric.title())}</th>' for metric in METRICS)
        performance_html = (
            '<div class="table-wrap"><table>'
            f'<thead><tr><th>Content</th><th>Platform</th><th>Observed</th><th>Basis</th>{metric_headers}<th>Source</th></tr></thead>'
            f'<tbody>{"".join(perf_rows)}</tbody></table></div>'
            '<p class="muted" style="margin:10px 0 0">Metrics retain their original platform meaning. Cumulative snapshots are shown by date and are not added together.</p>'
        )
    else:
        performance_html = empty(
            "No performance data yet. Published content remains visible while results are unavailable.",
            "Import a local CSV or XLSX export through Agent chat to populate this table.",
        )

    action_items = next_actions(calendar, performance)
    actions_html = '<ol class="actions-list">' + ''.join(
        f'<li class="action-row">'
        f'<div class="action-left"><span class="action-idx">{idx}</span><span class="action-text">{escape(text)}</span></div>'
        f'<button type="button" class="copy-btn" data-prompt="{escape(prompt, quote=True)}">Copy Prompt</button>'
        f'</li>'
        for idx, (text, prompt) in enumerate(action_items, 1)
    ) + '</ol>'

    initials = ''.join(word[0].upper() for word in brand_name.split()[:2]) or "CO"

    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Content Operations Workspace</title>
{CSS}
</head>
<body>
<div class="shell">
  <aside class="sidebar" aria-label="Workspace Navigation">
    <div>
      <div class="brand">
        <div class="brand-mark">CO</div>
        <div>
          <div class="brand-name">Content Ops</div>
          <div class="brand-sub">Local Workspace</div>
        </div>
      </div>
      <nav class="nav-wrap" id="nav-wrap">
        <div class="nav-pill" id="nav-pill"></div>
        <button type="button" class="nav-item active" data-section="overview">
          <svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>
          Overview
        </button>
        <button type="button" class="nav-item" data-section="calendar">
          <svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="17" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>
          Calendar
          <span class="nav-count">{len(upcoming)}</span>
        </button>
        <button type="button" class="nav-item" data-section="performance">
          <svg viewBox="0 0 24 24"><path d="M4 19h16M7 16V9M12 16V5M17 16v-4"/></svg>
          Performance
          <span class="nav-count">{len(performance)}</span>
        </button>
        <button type="button" class="nav-item" data-section="actions">
          <svg viewBox="0 0 24 24"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
          Next Actions
          <span class="nav-count">{len(action_items)}</span>
        </button>
      </nav>
    </div>
    <div class="sidebar-foot">
      <div class="avatar">{escape(initials)}</div>
      <div style="min-width:0">
        <div class="foot-title">{escape(brand_name)}</div>
        <div class="foot-sub">Offline · Local CSV</div>
      </div>
    </div>
  </aside>

  <main class="main">
    <header class="topbar">
      <div class="title-block">
        <h1>Content Operations Workspace</h1>
        <p class="title-sub">Plan · Create · Publish · Review — Local-first content studio</p>
      </div>
      <div class="toolbar">
        <div class="split-wrap" id="split-wrap">
          <button type="button" class="split-trigger" id="split-trigger">
            <span id="split-label">All Platforms</span>
            <span style="opacity:.55">⌄</span>
          </button>
          <div class="split-chips" id="split-chips">{split_chips_html}</div>
        </div>
        <div class="search-box" id="search-box">
          <input type="search" id="search-input" placeholder="Filter titles..." aria-label="Filter content titles">
        </div>
        <button type="button" class="icon-btn" id="search-toggle" title="Search content" aria-label="Search content">
          <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
        </button>
      </div>
    </header>

    <div class="bento" id="bento">
      <!-- KPI Row -->
      <section class="card span-3" data-tilt data-groups="overview">
        <div class="kpi-label">All content</div>
        <div class="kpi-row"><div class="kpi-val" id="kpi-all">{len(calendar)}</div><svg class="spark" viewBox="0 0 68 22"><path d="M2 18 L16 14 L28 16 L42 9 L54 11 L66 4"/></svg></div>
        <div class="kpi-foot"><span class="kpi-pill">Saved</span><span class="muted">Platform versions</span></div>
      </section>

      <section class="card span-3" data-tilt data-groups="overview">
        <div class="kpi-label">To make</div>
        <div class="kpi-row"><div class="kpi-val" id="kpi-make">{to_make}</div><svg class="spark" viewBox="0 0 68 22"><path d="M2 15 L18 17 L32 11 L46 13 L58 7 L66 8"/></svg></div>
        <div class="kpi-foot"><span class="kpi-pill soft">In progress</span><span class="muted">Idea, planned, draft</span></div>
      </section>

      <section class="card span-3" data-tilt data-groups="overview">
        <div class="kpi-label">Published</div>
        <div class="kpi-row"><div class="kpi-val" id="kpi-pub">{published}</div><svg class="spark" viewBox="0 0 68 22"><path d="M2 19 L18 16 L30 13 L44 10 L56 6 L66 3"/></svg></div>
        <div class="kpi-foot"><span class="kpi-pill">Confirmed</span><span class="muted">Verified releases</span></div>
      </section>

      <section class="card span-3" data-tilt data-groups="overview">
        <div class="kpi-label">Next 7 days</div>
        <div class="kpi-row"><div class="kpi-val" id="kpi-due">{due}</div><svg class="spark" viewBox="0 0 68 22"><path d="M2 14 L15 11 L29 14 L43 8 L55 10 L66 5"/></svg></div>
        <div class="kpi-foot"><span class="kpi-pill soft">Upcoming</span><span class="muted">Scheduled window</span></div>
      </section>

      <!-- Row 2: Pipeline Capsule Chart + Dark Hero Platform Card -->
      <section class="card span-7" data-tilt data-expandable data-groups="overview">
        <div class="card-head">
          <div>
            <h2 class="card-title">Status Breakdown</h2>
            <p class="card-sub">Editorial pipeline stages across saved records</p>
          </div>
          <div class="card-head-right">
            <span class="big-stat" id="pipeline-pct">{pub_pct}</span>
            <button type="button" class="expand-btn" title="Expand module">⤢</button>
          </div>
        </div>
        <div class="hide-mini" id="pipeline-body">{status_chart}</div>
      </section>

      <section class="card card-dark span-5" data-tilt data-expandable data-groups="overview">
        <div class="card-head">
          <div>
            <h2 class="card-title">Platform Mix</h2>
            <p class="card-sub">Channel distribution across workspace</p>
          </div>
          <div class="card-head-right">
            <button type="button" class="expand-btn" title="Expand module">⤢</button>
          </div>
        </div>
        <div class="dark-hero-num" id="platform-total">{len(calendar)}</div>
        <div class="muted">platform-specific versions</div>
        <div class="hide-mini" id="platform-body">{platform_chart}</div>
      </section>

      <!-- Row 3: Calendar / Upcoming -->
      <section class="card span-12" data-tilt data-expandable data-groups="overview calendar">
        <div class="card-head">
          <div>
            <h2 class="card-title">Content Calendar / Upcoming</h2>
            <p class="card-sub">Active editorial schedule — unconfirmed items never auto-publish</p>
          </div>
          <div class="card-head-right">
            <div class="view-switch">
              <button type="button" class="view-tab active" data-view="table">Table</button>
              <button type="button" class="view-tab" data-view="kanban">Board</button>
            </div>
            <button type="button" class="expand-btn" title="Expand module">⤢</button>
          </div>
        </div>
        <div class="hide-mini">
          <div id="calendar-table-wrap">{calendar_html}</div>
          <div class="kanban" id="calendar-kanban">{kanban_html}</div>
        </div>
      </section>

      <!-- Row 4: Performance Review -->
      <section class="card span-7" data-tilt data-expandable data-groups="overview performance">
        <div class="card-head">
          <div>
            <h2 class="card-title">Performance Review</h2>
            <p class="card-sub">Recorded metrics keep their platform meaning; missing values stay N/A</p>
          </div>
          <div class="card-head-right">
            <button type="button" class="expand-btn" title="Expand module">⤢</button>
          </div>
        </div>
        <div class="hide-mini" id="perf-body">{performance_html}</div>
      </section>

      <!-- Row 4 Right: Next Actions -->
      <section class="card span-5" data-tilt data-expandable data-groups="overview actions">
        <div class="card-head">
          <div>
            <h2 class="card-title">Next Actions</h2>
            <p class="card-sub">Copy a ready-to-send prompt directly into Agent chat</p>
          </div>
          <div class="card-head-right">
            <button type="button" class="expand-btn" title="Expand module">⤢</button>
          </div>
        </div>
        <div class="hide-mini" id="actions-body">{actions_html}</div>
      </section>
    </div>

    <footer class="foot-note">
      <span>Source of truth: <span class="path">workspace/content-calendar.csv</span> · <span class="path">workspace/performance.csv</span> · Markdown drafts</span>
      <span>Content Operations Workspace · Generated from local workspace files</span>
    </footer>
  </main>
</div>
<div class="toast" id="toast" role="status" aria-live="polite"></div>
{JS}
</body>
</html>
'''
