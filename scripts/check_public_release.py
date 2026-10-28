#!/usr/bin/env python3
"""Check that a repository copy is a clean public template, not a user workspace."""
from pathlib import Path
import re
import subprocess

from content_ops import ROOT, render_dashboard, validate_workspace


SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\b(?:sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,})\b"),
    re.compile(r"(?i)\b(?:api[_ -]?key|access[_ -]?token|client[_ -]?secret)\s*[:=]\s*[^\s<]{8,}"),
]


def main():
    errors, calendar, performance = validate_workspace(ROOT / "workspace")
    if calendar:
        errors.append("public template contains content-calendar records")
    if performance:
        errors.append("public template contains performance records")
    brand = (ROOT / "workspace/brand-context.md").read_text(encoding="utf-8")
    for line in brand.splitlines():
        if line.startswith("- ") and ":" in line and line.split(":", 1)[1].strip():
            errors.append("public template contains populated brand context")
            break
    for folder in (ROOT / "workspace/drafts", ROOT / "workspace/materials"):
        extras = [path for path in folder.iterdir() if path.name != ".gitkeep"]
        if extras:
            errors.append(f"public template contains user files in {folder.relative_to(ROOT)}")
    dashboard = (ROOT / "dashboard.html").read_text(encoding="utf-8") if (ROOT / "dashboard.html").is_file() else ""
    try:
        expected = render_dashboard(ROOT / "workspace")
        if dashboard != expected:
            errors.append("root dashboard is not generated from the blank workspace")
    except ValueError as error:
        errors.append(str(error))
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".xlsx"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(pattern.search(text) for pattern in SECRET_PATTERNS):
            errors.append(f"potential credential in {path.relative_to(ROOT)}")
    if errors:
        print("FAILED Template Release Mode")
        print("\n".join(errors))
        return 1
    if (ROOT / ".git").exists():
        status = subprocess.run(["git", "status", "--short"], cwd=ROOT, capture_output=True, text=True)
        git_state = "Clean" if status.returncode == 0 and not status.stdout.strip() else "Working Tree Has Changes"
    else:
        git_state = "Skipped — Not a Git Repository"
    print(f"OK Template Release Mode: blank workspace, blank-derived dashboard and public text scan; Git status: {git_state}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

