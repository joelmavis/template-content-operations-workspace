#!/usr/bin/env python3
"""Incrementally import local CSV/XLSX performance results without summing snapshots."""
from argparse import ArgumentParser
from datetime import date, datetime, timedelta
from pathlib import Path
import re
import sys

from content_ops import PERFORMANCE_FIELDS, METRICS, ROOT, number, read_csv, write_csv
from local_table import read_local_table


ALIASES = {
    "performance_id": ("performance_id", "performance id", "record_id", "记录id"),
    "content_id": ("content_id", "content id", "内容id"),
    "title": ("title", "content title", "post title", "标题", "内容标题"),
    "platform": ("platform", "channel", "平台", "渠道"),
    "observed_date": ("observed_date", "observed date", "date", "统计日期", "日期"),
    "metric_basis": ("metric_basis", "metric basis", "basis", "口径", "数据口径"),
    "impressions": ("impressions", "impression", "曝光", "展示次数"),
    "views": ("views", "view", "播放量", "浏览量"),
    "reads": ("reads", "read", "阅读量", "阅读数"),
    "likes": ("likes", "like", "点赞", "点赞数"),
    "comments": ("comments", "comment", "评论", "评论数"),
    "shares": ("shares", "share", "分享", "转发", "转发数"),
    "clicks": ("clicks", "click", "点击", "点击数"),
    "downloads": ("downloads", "download", "下载", "下载量"),
    "installs": ("installs", "install", "安装", "安装量"),
    "source_reference": ("source_reference", "source", "source file", "来源", "数据来源"),
    "notes": ("notes", "note", "备注"),
}


def normalized(value):
    return re.sub(r"[\s_\-]+", " ", str(value).strip().lower())


def alias_map(headers):
    lookup = {normalized(header): header for header in headers}
    return {field: next((lookup[normalized(alias)] for alias in aliases if normalized(alias) in lookup), None) for field, aliases in ALIASES.items()}


def next_id(rows):
    used = {row["performance_id"] for row in rows}
    index = 1
    while True:
        candidate = f"PERF-{date.today().strftime('%Y%m%d')}-{index:03d}"
        if candidate not in used:
            return candidate
        index += 1


def observed_date(value):
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("observed date is required")
    if re.fullmatch(r"\d+(?:\.0+)?", raw):
        serial = int(float(raw))
        if 1 <= serial <= 100000:
            return (date(1899, 12, 30) + timedelta(days=serial)).isoformat()
    for pattern in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y年%m月%d日"):
        try:
            return datetime.strptime(raw, pattern).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f"invalid observed date '{raw}'")


def import_rows(root, input_path, dry_run=False):
    root = Path(root)
    input_path = Path(input_path)
    headers, source_rows = read_local_table(input_path)
    mapping = alias_map(headers)
    calendar = read_csv(root / "workspace/content-calendar.csv", [
        "content_id", "content_group_id", "title", "platform", "format", "theme", "planned_date", "status", "draft_path", "published_date", "published_url", "cta_url", "source_reference", "last_updated", "notes"
    ])
    performance = read_csv(root / "workspace/performance.csv", PERFORMANCE_FIELDS)
    by_id = {row["content_id"]: row for row in calendar}
    by_name = {}
    for row in calendar:
        by_name.setdefault((normalized(row["title"]), normalized(row["platform"])), []).append(row)
    existing = {(row["content_id"], row["observed_date"], row["metric_basis"]): row for row in performance}
    merged = 0
    created = 0
    errors = []
    for source_number, source in enumerate(source_rows, 2):
        get = lambda field: str(source.get(mapping.get(field), "")).strip() if mapping.get(field) else ""
        content_id = get("content_id")
        platform = get("platform")
        if content_id:
            content = by_id.get(content_id)
        else:
            matches = by_name.get((normalized(get("title")), normalized(platform)), [])
            content = matches[0] if len(matches) == 1 else None
            if len(matches) > 1:
                errors.append(f"row {source_number}: title and platform match more than one content record")
        if not content:
            errors.append(f"row {source_number}: cannot match content by ID or unambiguous title plus platform")
            continue
        platform = platform or content["platform"]
        if normalized(platform) != normalized(content["platform"]):
            errors.append(f"row {source_number}: platform does not match {content['title']}")
            continue
        raw_observed = get("observed_date")
        basis = get("metric_basis") or "Cumulative"
        try:
            observed = observed_date(raw_observed)
        except ValueError as error:
            errors.append(f"row {source_number}: {error}")
            continue
        values = {metric: get(metric).replace(",", "") for metric in METRICS}
        try:
            for metric, value in values.items():
                number(value)
        except ValueError as error:
            errors.append(f"row {source_number}: {metric} has {error}")
            continue
        if not any(values.values()):
            errors.append(f"row {source_number}: at least one metric is required")
            continue
        key = (content["content_id"], observed, basis)
        target = existing.get(key)
        if target:
            conflict = False
            for metric, value in values.items():
                if value and target[metric] and value != target[metric]:
                    errors.append(f"row {source_number}: conflicting {metric} for existing snapshot {content['title']} / {observed}")
                    conflict = True
            if conflict:
                continue
            for metric, value in values.items():
                if value and not target[metric]:
                    target[metric] = value
            if get("notes") and get("notes") not in target["notes"]:
                target["notes"] = "; ".join(filter(None, [target["notes"], get("notes")]))
            merged += 1
        else:
            target = {field: "" for field in PERFORMANCE_FIELDS}
            target.update({
                "performance_id": get("performance_id") or next_id(performance),
                "content_id": content["content_id"],
                "platform": content["platform"],
                "observed_date": observed,
                "metric_basis": basis,
                "source_reference": get("source_reference") or input_path.name,
                "notes": get("notes"),
                **values,
            })
            performance.append(target)
            existing[key] = target
            created += 1
    if errors:
        raise ValueError("; ".join(errors))
    if not dry_run:
        write_csv(root / "workspace/performance.csv", PERFORMANCE_FIELDS, performance)
    return created, merged, len(performance)


def main(argv=None):
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        created, merged, total = import_rows(args.root.resolve(), args.input.resolve(), args.dry_run)
    except (OSError, ValueError) as error:
        print(f"Import stopped: {error}", file=sys.stderr)
        return 1
    print(f"Performance import {'checked' if args.dry_run else 'saved'}: {created} created, {merged} safely merged, {total} total snapshots.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

