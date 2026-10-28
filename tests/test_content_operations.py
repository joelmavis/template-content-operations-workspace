#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from content_ops import CALENDAR_FIELDS, PERFORMANCE_FIELDS, read_csv, render_dashboard, validate_workspace, write_csv
from import_performance import import_rows, observed_date
from local_table import read_local_table


def copy_repo():
    temporary = tempfile.TemporaryDirectory(prefix="content-ops-test-")
    target = Path(temporary.name) / "repo"
    shutil.copytree(ROOT, target, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
    return temporary, target


def calendar_rows(root):
    rows = []
    specs = [
        ("CONTENT-001", "Developer workflow lesson", "X", "Short post", "2026-11-02", "Ready"),
        ("CONTENT-002", "Developer workflow guide", "Medium", "Article", "2026-11-03", "Published"),
        ("CONTENT-003", "Interview insight thread", "X", "Thread", "2026-11-04", "Published"),
        ("CONTENT-004", "Local-first checklist", "LinkedIn", "Post", "", "Drafting"),
        ("CONTENT-005", "Weekly build note", "Unknown Community", "Update", "2026-11-06", "Planned"),
    ]
    for index, (content_id, title, platform, format_name, planned, status) in enumerate(specs, 1):
        draft_rel = f"workspace/drafts/{content_id.lower()}.md"
        (root / draft_rel).write_text(f"# {title}\n\n- Platform: {platform}\n- Audience: Developers\n- Status: {status}\n\n## Draft\n\nSource-supported draft {index}.\n\n## CTA\n\nReview locally.\n\n## Sources\n\nLocal brief.\n\n## Open questions\n\nNone recorded.\n", encoding="utf-8")
        rows.append({
            "content_id": content_id,
            "content_group_id": "GROUP-001" if index <= 2 else f"GROUP-{index:03d}",
            "title": title,
            "platform": platform,
            "format": format_name,
            "theme": "Practical workflow",
            "planned_date": planned,
            "status": status,
            "draft_path": draft_rel,
            "published_date": "2026-10-27" if status == "Published" else "",
            "published_url": "" if status == "Published" else "",
            "cta_url": "",
            "source_reference": "local-product-brief.md",
            "last_updated": "2026-10-28",
            "notes": "Publication URL pending" if status == "Published" else "",
        })
    return rows


def write_source(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


class ContentOperationsTests(unittest.TestCase):
    def test_01_blank_workspace_renders_actionable_empty_state(self):
        html = render_dashboard(ROOT / "workspace")
        self.assertIn("No upcoming content yet", html)
        self.assertIn("Describe a content goal or attach local materials", html)
        self.assertNotIn("example", html.lower())

    def test_02_complete_workflow_with_partial_metrics(self):
        temporary, root = copy_repo()
        self.addCleanup(temporary.cleanup)
        brand = root / "workspace/brand-context.md"
        brand.write_text(brand.read_text(encoding="utf-8").replace("- Brand or project:", "- Brand or project: Local Product"), encoding="utf-8")
        write_csv(root / "workspace/content-calendar.csv", CALENDAR_FIELDS, calendar_rows(root))
        source = root / "results.csv"
        write_source(source, ["内容标题", "平台", "日期", "播放量", "点击数"], [
            {"内容标题": "Developer workflow guide", "平台": "Medium", "日期": "2026-10-28", "播放量": "1200", "点击数": ""},
            {"内容标题": "Interview insight thread", "平台": "X", "日期": "2026-10-28", "播放量": "", "点击数": "86"},
        ])
        created, merged, total = import_rows(root, source)
        self.assertEqual((created, merged, total), (2, 0, 2))
        html = render_dashboard(root / "workspace", today=None)
        self.assertIn("Developer workflow guide", html)
        self.assertIn("Interview insight thread", html)
        self.assertIn(">1,200<", html)
        self.assertIn(">86<", html)
        self.assertIn(">N/A<", html)
        errors, calendar, performance = validate_workspace(root / "workspace")
        self.assertEqual(errors, [])
        self.assertEqual((len(calendar), len(performance)), (5, 2))

    def test_03_duplicate_snapshot_safely_merges_missing_metric(self):
        temporary, root = copy_repo()
        self.addCleanup(temporary.cleanup)
        write_csv(root / "workspace/content-calendar.csv", CALENDAR_FIELDS, calendar_rows(root))
        first = root / "first.csv"
        write_source(first, ["content_id", "platform", "observed_date", "views"], [{"content_id": "CONTENT-002", "platform": "Medium", "observed_date": "2026-10-28", "views": "1200"}])
        import_rows(root, first)
        second = root / "second.csv"
        write_source(second, ["content_id", "platform", "observed_date", "views", "clicks"], [{"content_id": "CONTENT-002", "platform": "Medium", "observed_date": "2026-10-28", "views": "1200", "clicks": "45"}])
        created, merged, total = import_rows(root, second)
        self.assertEqual((created, merged, total), (0, 1, 1))
        rows = read_csv(root / "workspace/performance.csv", PERFORMANCE_FIELDS)
        self.assertEqual((rows[0]["views"], rows[0]["clicks"]), ("1200", "45"))

    def test_04_conflicting_duplicate_is_rejected_without_overwrite(self):
        temporary, root = copy_repo()
        self.addCleanup(temporary.cleanup)
        write_csv(root / "workspace/content-calendar.csv", CALENDAR_FIELDS, calendar_rows(root))
        source = root / "first.csv"
        write_source(source, ["content_id", "platform", "observed_date", "views"], [{"content_id": "CONTENT-002", "platform": "Medium", "observed_date": "2026-10-28", "views": "1200"}])
        import_rows(root, source)
        conflict = root / "conflict.csv"
        write_source(conflict, ["content_id", "platform", "observed_date", "views"], [{"content_id": "CONTENT-002", "platform": "Medium", "observed_date": "2026-10-28", "views": "900"}])
        with self.assertRaisesRegex(ValueError, "conflicting views"):
            import_rows(root, conflict)
        rows = read_csv(root / "workspace/performance.csv", PERFORMANCE_FIELDS)
        self.assertEqual(rows[0]["views"], "1200")

    def test_05_invalid_number_is_rejected(self):
        temporary, root = copy_repo()
        self.addCleanup(temporary.cleanup)
        write_csv(root / "workspace/content-calendar.csv", CALENDAR_FIELDS, calendar_rows(root))
        source = root / "bad.csv"
        write_source(source, ["content_id", "platform", "observed_date", "views"], [{"content_id": "CONTENT-002", "platform": "Medium", "observed_date": "2026-10-28", "views": "many"}])
        with self.assertRaisesRegex(ValueError, "invalid number"):
            import_rows(root, source)
        self.assertEqual(read_csv(root / "workspace/performance.csv", PERFORMANCE_FIELDS), [])

    def test_06_missing_plan_date_and_published_url_are_allowed(self):
        temporary, root = copy_repo()
        self.addCleanup(temporary.cleanup)
        rows = calendar_rows(root)
        self.assertEqual(rows[3]["planned_date"], "")
        self.assertEqual(rows[1]["published_url"], "")
        write_csv(root / "workspace/content-calendar.csv", CALENDAR_FIELDS, rows)
        errors, _, _ = validate_workspace(root / "workspace")
        self.assertEqual(errors, [])

    def test_07_unknown_platform_and_duplicate_titles_are_allowed(self):
        temporary, root = copy_repo()
        self.addCleanup(temporary.cleanup)
        rows = calendar_rows(root)
        rows[4]["title"] = rows[0]["title"]
        write_csv(root / "workspace/content-calendar.csv", CALENDAR_FIELDS, rows)
        errors, _, _ = validate_workspace(root / "workspace")
        self.assertEqual(errors, [])
        html = render_dashboard(root / "workspace")
        self.assertIn("Unknown Community", html)

    def test_08_renderer_preserves_last_valid_dashboard_on_error(self):
        temporary, root = copy_repo()
        self.addCleanup(temporary.cleanup)
        original = (root / "dashboard.html").read_text(encoding="utf-8")
        (root / "workspace/content-calendar.csv").write_text("wrong,header\n1,2\n", encoding="utf-8")
        import subprocess
        result = subprocess.run([sys.executable, "scripts/render_dashboard.py", "--root", str(root)], cwd=root, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((root / "dashboard.html").read_text(encoding="utf-8"), original)

    def test_09_drafts_survive_incremental_performance_import(self):
        temporary, root = copy_repo()
        self.addCleanup(temporary.cleanup)
        rows = calendar_rows(root)
        write_csv(root / "workspace/content-calendar.csv", CALENDAR_FIELDS, rows)
        draft = root / rows[0]["draft_path"]
        before = draft.read_text(encoding="utf-8")
        source = root / "result.csv"
        write_source(source, ["content_id", "platform", "observed_date", "likes"], [{"content_id": "CONTENT-002", "platform": "Medium", "observed_date": "2026-10-28", "likes": "31"}])
        import_rows(root, source)
        self.assertEqual(draft.read_text(encoding="utf-8"), before)

    def test_10_html_is_single_offline_names_first_dashboard(self):
        html = render_dashboard(ROOT / "workspace")
        self.assertNotRegex(html, r"<script[^>]+src=|<link[^>]+href=['\"]https?://")
        self.assertEqual(len(list(ROOT.glob("*.html"))), 1)
        self.assertIn("Content Operations Workspace", html)

    def test_11_agent_rules_preserve_publish_boundary_and_handoff(self):
        rules = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("Time passing never advances status automatically", rules)
        self.assertIn("Do not connect social accounts", rules)
        self.assertTrue((ROOT / "HANDOFF.md").is_file())

    def test_12_cumulative_snapshots_remain_separate_rows(self):
        temporary, root = copy_repo()
        self.addCleanup(temporary.cleanup)
        write_csv(root / "workspace/content-calendar.csv", CALENDAR_FIELDS, calendar_rows(root))
        source = root / "snapshots.csv"
        write_source(source, ["content_id", "platform", "observed_date", "metric_basis", "views"], [
            {"content_id": "CONTENT-002", "platform": "Medium", "observed_date": "2026-10-28", "metric_basis": "Cumulative", "views": "1200"},
            {"content_id": "CONTENT-002", "platform": "Medium", "observed_date": "2026-10-29", "metric_basis": "Cumulative", "views": "1500"},
        ])
        import_rows(root, source)
        rows = read_csv(root / "workspace/performance.csv", PERFORMANCE_FIELDS)
        self.assertEqual([row["views"] for row in rows], ["1200", "1500"])
        html = render_dashboard(root / "workspace")
        self.assertIn("Cumulative snapshots are shown by date and are not added together", html)

    def test_13_xlsx_local_table_is_supported(self):
        temporary, root = copy_repo()
        self.addCleanup(temporary.cleanup)
        path = root / "results.xlsx"
        with ZipFile(path, "w") as archive:
            archive.writestr("xl/workbook.xml", '<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Results" sheetId="1" r:id="rId1"/></sheets></workbook>')
            archive.writestr("xl/_rels/workbook.xml.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
            archive.writestr("xl/worksheets/sheet1.xml", '<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>title</t></is></c><c r="B1" t="inlineStr"><is><t>views</t></is></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>Local guide</t></is></c><c r="B2"><v>321</v></c></row></sheetData></worksheet>')
        headers, rows = read_local_table(path)
        self.assertEqual(headers, ["title", "views"])
        self.assertEqual(rows, [{"title": "Local guide", "views": "321"}])

    def test_14_common_and_excel_dates_are_normalized(self):
        self.assertEqual(observed_date("2026/10/28"), "2026-10-28")
        self.assertEqual(observed_date("2026年10月28日"), "2026-10-28")
        self.assertEqual(observed_date("46323"), "2026-10-28")


if __name__ == "__main__":
    unittest.main()

