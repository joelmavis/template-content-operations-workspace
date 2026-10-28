#!/usr/bin/env python3
"""Render the single Content Operations Workspace dashboard safely."""
from argparse import ArgumentParser
from pathlib import Path
import sys

from content_ops import ROOT, render_dashboard


def main(argv=None):
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    target = root / "dashboard.html"
    temporary = target.with_suffix(".html.tmp")
    try:
        html = render_dashboard(root / "workspace")
        temporary.write_text(html, encoding="utf-8")
        temporary.replace(target)
    except (OSError, ValueError) as error:
        if temporary.exists():
            temporary.unlink()
        print(f"Dashboard not changed: {error}", file=sys.stderr)
        return 1
    print(f"Rendered {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

