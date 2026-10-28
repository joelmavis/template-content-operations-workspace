#!/usr/bin/env python3
"""Validate populated user data without requiring a blank public template."""
from argparse import ArgumentParser
from pathlib import Path
import re
import subprocess

from content_ops import ROOT, validate_workspace


def warn_if_public_remote(root):
    if not (root / ".git").exists():
        return
    result = subprocess.run(["git", "remote", "get-url", "origin"], cwd=root, capture_output=True, text=True)
    remote = result.stdout.strip()
    if result.returncode == 0 and ("github.com" in remote or "gitlab.com" in remote):
        print("WARNING: This workspace is connected to a hosted Git remote. Validation does not make drafts, materials or results safe to publish.")


def main(argv=None):
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    errors = []
    for path in ("README.md", "AGENTS.md", "PLAYBOOK.md", "workspace/brand-context.md", "dashboard.html"):
        if not (root / path).is_file():
            errors.append(f"missing {path}")
    for path in ("workspace/drafts", "workspace/materials", "scripts", "tests"):
        if not (root / path).is_dir():
            errors.append(f"missing {path}/")
    data_errors, calendar, performance = validate_workspace(root / "workspace")
    errors.extend(data_errors)
    dashboard = (root / "dashboard.html").read_text(encoding="utf-8") if (root / "dashboard.html").is_file() else ""
    if "Content Operations Workspace" not in dashboard:
        errors.append("dashboard lacks product title")
    if re.search(r"<script[^>]+src=|<link[^>]+href=['\"]https?://", dashboard, re.I):
        errors.append("dashboard depends on an external asset")
    if len(list(root.glob("*.html"))) != 1:
        errors.append("repository must contain exactly one root HTML dashboard")
    for row in calendar:
        if row["title"] not in dashboard or row["platform"] not in dashboard:
            errors.append(f"dashboard does not show {row['title']} / {row['platform']}")
    if not calendar and "No upcoming content yet" not in dashboard:
        errors.append("blank dashboard lacks actionable Empty State")
    for row in performance:
        if row["performance_id"] not in dashboard:
            errors.append(f"dashboard does not show performance record {row['performance_id']}")
    if errors:
        print("FAILED")
        print("\n".join(errors))
        return 1
    print(f"PASSED User Workspace Mode: {len(calendar)} content records, {len(performance)} performance snapshots; relationships, partial metrics, names-first HTML and local assets checked.")
    warn_if_public_remote(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

