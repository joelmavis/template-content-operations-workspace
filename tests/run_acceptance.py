#!/usr/bin/env python3
"""Run the Brief's ten-step workflow in a disposable copy."""
from pathlib import Path
import csv
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from content_ops import CALENDAR_FIELDS, PERFORMANCE_FIELDS, next_actions, read_csv, validate_workspace, write_csv
from import_performance import import_rows


def run(root, *args):
    result = subprocess.run([sys.executable, *args], cwd=root, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout


def draft_text(title, platform, status):
    return f"# {title}\n\n- Platform: {platform}\n- Audience: Product builders\n- Status: {status}\n\n## Draft\n\nA practical, source-bounded draft.\n\n## CTA\n\nContinue in the local workspace.\n\n## Sources\n\nLocal product brief.\n\n## Open questions\n\nNone recorded.\n"


def write_input(path, rows):
    fields = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


with tempfile.TemporaryDirectory(prefix="content-ops-acceptance-") as temporary:
    root = Path(temporary) / "repo"
    shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))

    # 1. Clean start.
    run(root, "scripts/render_dashboard.py", "--root", str(root))
    assert "No upcoming content yet" in (root / "dashboard.html").read_text(encoding="utf-8")

    # 2. Brand context from conversation.
    brand = root / "workspace/brand-context.md"
    text = brand.read_text(encoding="utf-8")
    text = text.replace("- Brand or project:", "- Brand or project: Local Tool")
    text = text.replace("- Target audience:", "- Target audience: Independent developers")
    text = text.replace("- Primary channels:", "- Primary channels: X, Medium")
    text = text.replace("- Voice and style:", "- Voice and style: Formal, practical, concrete")
    brand.write_text(text, encoding="utf-8")

    # 3–4. Seven-day plan and five usable drafts.
    specs = [
        ("C-001", "G-001", "Local workflow tip", "X", "Short post", "2026-11-01", "Ready"),
        ("C-002", "G-001", "Local workflow guide", "Medium", "Article", "2026-11-02", "Ready"),
        ("C-003", "G-002", "Evidence before claims", "X", "Thread", "2026-11-03", "Ready"),
        ("C-004", "G-003", "Agent handoff checklist", "Medium", "Article", "2026-11-05", "Drafting"),
        ("C-005", "G-004", "Weekly build note", "X", "Short post", "2026-11-07", "Planned"),
    ]
    calendar = []
    for content_id, group_id, title, platform, format_name, planned, status in specs:
        draft_path = f"workspace/drafts/{content_id.lower()}.md"
        (root / draft_path).write_text(draft_text(title, platform, status), encoding="utf-8")
        calendar.append(dict(zip(CALENDAR_FIELDS, [content_id, group_id, title, platform, format_name, "Local-first operations", planned, status, draft_path, "", "", "", "product-brief.md", "2026-10-28", ""])))

    # 5. Only two explicit publications advance.
    for row in calendar[:2]:
        row["status"] = "Published"
        row["published_date"] = "2026-10-28"
    calendar[0]["published_url"] = "https://example.com/p/local-workflow-tip"
    calendar[1]["notes"] = "Published URL pending"
    write_csv(root / "workspace/content-calendar.csv", CALENDAR_FIELDS, calendar)
    assert sum(row["status"] == "Published" for row in calendar) == 2

    # 6. Partial results: views for one item, clicks for another.
    first = root / "results-one.csv"
    write_input(first, [
        {"content_id": "C-001", "platform": "X", "observed_date": "2026-10-28", "views": "820", "clicks": ""},
        {"content_id": "C-002", "platform": "Medium", "observed_date": "2026-10-28", "views": "", "clicks": "47"},
    ])
    import_rows(root, first)
    run(root, "scripts/render_dashboard.py", "--root", str(root))
    html = (root / "dashboard.html").read_text(encoding="utf-8")
    assert ">N/A<" in html and "Local workflow tip" in html

    # 7. Incremental result and draft edit preserve history.
    draft = root / "workspace/drafts/c-004.md"
    draft.write_text(draft.read_text(encoding="utf-8") + "\n## Revision\n\nClarified the handoff boundary.\n", encoding="utf-8")
    second = root / "results-two.csv"
    write_input(second, [{"content_id": "C-001", "platform": "X", "observed_date": "2026-10-28", "views": "820", "clicks": "29"}])
    import_rows(root, second)
    assert "Clarified the handoff boundary" in draft.read_text(encoding="utf-8")

    # 8. A continuing Agent can derive specific work from files.
    performance = read_csv(root / "workspace/performance.csv", PERFORMANCE_FIELDS)
    actions = next_actions(calendar, performance)
    assert any("Evidence before claims" in action for action in actions)

    # 9. Repeated identical import does not duplicate the snapshot.
    import_rows(root, second)
    assert len(read_csv(root / "workspace/performance.csv", PERFORMANCE_FIELDS)) == 2

    # 10. Full validation and generation.
    run(root, "scripts/render_dashboard.py", "--root", str(root))
    errors, final_calendar, final_performance = validate_workspace(root / "workspace")
    assert not errors and len(final_calendar) == 5 and len(final_performance) == 2
    run(root, "scripts/validate_workspace.py", "--root", str(root))

print("PASSED 10-step disposable acceptance: clean start → context → 7-day plan → 5 drafts → 2 publications → partial results → incremental update → Agent continuation → duplicate protection → validation.")

