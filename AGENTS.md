# Shared Agent Rules

The user works through conversation. Manage the files on their behalf and keep the workflow non-developer first.

## Before every action

Read `PLAYBOOK.md`, `workspace/brand-context.md`, both workspace CSV files, relevant Markdown drafts and the latest `HANDOFF.md` entry. Continue from recorded state; never rebuild the workspace from chat memory alone.

## Starting modes

Support exactly two local-first input modes:

1. natural-language goals, brand context, status updates or results supplied by the user;
2. readable local files or attachments, including briefs, notes, CSV and XLSX tables.

The three business entrances are Plan from Goal, Create from Materials and Review from Results. Do not add pasted-URL ingestion as another input mode. URLs already present in local records may be retained as publishing, CTA or source references, but their presence is not proof that linked content was read.

## Truth and state

- Never invent a product capability, quote, customer example, publication, URL, date or metric.
- `Drafting`, `Ready` and `Scheduled` are not `Published`. Only explicit user confirmation or inspectable evidence may set `Published`.
- Time passing never advances status automatically.
- Preserve unknown values as blank. In HTML, display missing metrics as `N/A`, never as zero.
- Keep platform metric meanings separate. Do not equate impressions, views and reads or compare unlike windows as if they were the same measure.
- When the user changes a fact, preserve prior useful records and update only the intended fields.

## File ownership

- `workspace/brand-context.md` stores durable brand facts, audiences, channels, voice, exclusions, CTA guidance and material references.
- `workspace/content-calendar.csv` owns one row per platform-specific content item. Use stable `content_id` values and optional `content_group_id` values for related cross-platform versions.
- `workspace/performance.csv` owns observed results. A row may contain only one metric. Use `metric_basis` to distinguish cumulative snapshots from period values when known.
- `workspace/drafts/` stores readable Markdown drafts. Lead with titles, platforms and status; IDs are secondary traceability details.
- `workspace/materials/` contains only local files the user explicitly authorizes for persistence. If an attachment is readable but cannot be saved, say so and store only a safe source summary.

## Writing and importing

- Import incrementally. Map recognizable column names, preserve source references, deduplicate safely and stop on conflicting duplicate snapshots rather than summing them.
- Never clear the calendar, drafts, materials or performance history to simplify an update.
- Before overwriting a non-empty field, confirm the new value is an intended correction.
- A repeated title is allowed. Use the stable ID and platform to distinguish records.
- Adapt content to each platform; changing only the platform label is not a completed adaptation.
- Every draft needs a readable title, platform, audience, body, CTA when applicable, source notes, status and open questions.

## External actions

- Drafting does not authorize publishing.
- Do not connect social accounts, post, schedule externally, send messages, read private analytics or use third-party APIs in v1.0.
- Follow the user’s language. Keep UI copy clear and name-first.

## After a meaningful change

1. save source files first;
2. run `python3 scripts/validate_workspace.py`;
3. run `python3 scripts/render_dashboard.py`;
4. add a concise handoff entry explaining evidence, changes and exact next action.

Normal validation accepts populated user data. Never delete user content to make a public-template check pass. If this checkout still points to a public Git remote, warn that real drafts and results could be committed accidentally.

