# Content Operations Workspace v1.0 — QA

**Assessment date:** 2026-10-28  
**Automated environment:** local macOS runtime, Python standard library only

## Result

| Area | Status | Evidence |
|---|---|---|
| Blank first run | Passed | Empty Workspace generated an actionable Dashboard with no sample content. |
| Brand context and seven-day planning | Passed | Disposable acceptance created local brand context and five platform-specific calendar records. |
| Markdown drafts | Passed | Five linked drafts were created with title, platform, audience, body, CTA, sources, status and open questions. |
| Publishing truth boundary | Passed | Exactly two explicitly confirmed items moved to `Published`; scheduled/ready/drafting records did not advance automatically. |
| Partial performance data | Passed | One views-only and one clicks-only record imported; missing metrics rendered as `N/A`. |
| CSV/XLSX support | Passed | CSV field aliases and a local XLSX worksheet were read using the Python standard library. Common and Excel-serial dates normalized to ISO dates. |
| Incremental updates | Passed | A second result batch and draft revision preserved earlier drafts, calendar rows and snapshots. |
| Duplicate protection | Passed | Identical snapshots merged without duplication; conflicting values were rejected without overwrite. |
| Cumulative snapshots | Passed | Separate cumulative dates remained separate rows and were not summed. |
| Names-first UI | Passed | Dashboard tables lead with titles, platforms, dates and statuses; internal IDs are secondary. |
| Offline Dashboard | Passed | One root `dashboard.html`, inline CSS/SVG only, no CDN or external script. |
| Error recovery | Passed | Invalid CSV schema and invalid numbers stopped the operation; the previous valid Dashboard remained unchanged. |
| Automated tests | Passed | 14/14 unit tests passed. |
| 10-step Brief acceptance | Passed | Disposable run completed clean start → context → plan → drafts → publication → partial results → incremental update → Agent continuation → duplicate import → final validation. |

## Commands

```sh
python3 scripts/render_dashboard.py
python3 scripts/validate_workspace.py
python3 -m unittest discover -s tests -v
python3 tests/run_acceptance.py
python3 scripts/check_public_release.py
```

## PuppyOne Desktop — manual verification still required

- Open the clean folder and confirm the Dashboard renders at wide and narrow panel widths.
- Start from a natural-language goal and confirm an Agent creates the first plan without asking the user to edit files.
- Attach Markdown, PDF, DOCX, CSV and XLSX files and confirm which formats are readable and persist across sessions.
- Confirm an unreadable or non-persistent attachment produces an honest limitation message and safe source summary.
- Continue the same populated Workspace with a second configured Agent and confirm it reads files rather than rebuilding the project.
- Confirm HTML preview link limitations do not block the workflow; all key actions must remain available through Agent conversation and the file tree.
- Confirm Chrome and Safari rendering visually matches the Desktop preview.

No social account connection, automatic posting, private analytics access or third-party API integration was tested or implemented.

