# Content Operations Playbook

## 1. Input

Start from a natural-language goal/status update or readable local files. Record only facts and material the user supplied or authorized. Ask the fewest questions needed to clarify audience, channels, cadence, objective, voice or measurement meaning.

## 2. Plan

Update `brand-context.md`, then create platform-specific rows in `content-calendar.csv`. Related versions may share a `content_group_id`, but each platform has its own status, date, draft and performance. Preserve existing rows during replanning.

## 3. Draft

Create one Markdown file per platform version. Include title, platform, audience, status, body, CTA, source notes and open questions. Link the path from the calendar. Facts from materials must remain traceable; unsupported claims stay out.

## 4. Track publishing

Move content through `Idea → Planned → Drafting → Ready → Scheduled → Published`, with optional `Paused` or `Cancelled`. Never advance to `Published` because a scheduled date passed. Record the actual date and URL when supplied; a confirmed publication may have a blank URL with a note that it is pending.

## 5. Import results

Accept local CSV/XLSX files or a natural-language result update. Match by stable ID or unambiguous title plus platform. Preserve blank metrics, reject invalid numbers and conflicting duplicate snapshots, and never sum repeated cumulative snapshots. Save the local source name in `source_reference`.

## 6. Review

Separate:

- **Evidence:** recorded publication state and metrics;
- **Interpretation:** a bounded reading of comparable records;
- **Recommendation:** the next content action.

Do not rank unlike platform metrics as one universal score. Prefer title- and platform-specific observations.

## 7. Update the next plan

Change only future or explicitly selected records. Keep published content, source drafts and historical performance intact. When asked “What should I do today?”, return one to three actions from actual state rather than generating duplicate work.

## Recovery

- **Unreadable attachment:** explain the limit and ask for a readable local export; never claim the original was saved.
- **Missing dates:** keep the plan row and date blank.
- **Missing publication URL:** allow a user-confirmed publication, leave the URL blank and note that it is pending.
- **Malformed input:** do not overwrite source CSVs or the last valid Dashboard. Explain the row and field that failed.
- **Duplicate result:** merge only new blank fields; reject conflicting values until the user confirms a correction.
- **Agent handoff:** read files and `HANDOFF.md`, then continue without asking the user to reconstruct history.

