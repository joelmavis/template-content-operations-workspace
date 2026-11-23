# Content Operations Workspace

> **Plan, draft, track publishing, and review results in one local workspace — no spreadsheets to hand-edit, no cloud lock-in.**

[![License: MIT](https://img.shields.io/badge/License-MIT-amber.svg)](./LICENSE)
[![Offline First](https://img.shields.io/badge/Dashboard-Single--File%20Offline-c67647)](#)

A community-built local workspace template for running multi-platform content operations (X, Medium, LinkedIn, YouTube, newsletters, etc.) through natural conversation with an AI Agent.

---

## Quickstart Guide (3 Simple Steps)

You never need to create folders, hand-edit CSV files, or run commands manually—the Agent manages everything for you.

### Step 1: Get This Template
- **Option A (Recommended in Puppyone):** Click **"Use this template" (使用此模版)** on the Puppyone template details page to spin up a workspace immediately.
- **Option B (Git Clone):** Clone this repository locally and open the folder:
  ```bash
  git clone https://github.com/joelmavis/template-content-operations-workspace.git
  cd template-content-operations-workspace
  ```

### Step 2: Preview the Interactive Dashboard
1. In the left file tree, click **`dashboard.html`** to open the built-in HTML preview directly (no external browser or local server required).
2. Because this template starts clean, click **`Demo Preview`** in the top-right corner of the dashboard to preview the full frosted-glass Bento layout, pipeline charts, Kanban board, and performance review with read-only sample data (your local CSVs stay untouched).

### Step 3: Send Your First Prompt to the Agent
Open the **Agent Chat** panel and copy-paste one of the starting prompts below (or attach a local product brief / notes / CSV / XLSX file):

- **Plan from a goal:**
  ```text
  Create a 7-day X and Medium content plan for an AI developer tool targeting indie builders.
  ```
- **Create from local materials:**
  ```text
  Use the product brief and interview notes I attached to draft one Medium article and two X posts.
  ```
- **Import results & review:**
  ```text
  Import this local performance table and tell me what to repeat or change next week.
  ```

After every meaningful update, the Agent automatically validates the workspace and refreshes `dashboard.html`.

---

## Common Agent Prompts Cheat Sheet

| Goal | Where to Input | Prompt to Copy & Send |
| :--- | :--- | :--- |
| **Start a weekly plan** | Agent Chat | `Create a 7-day content plan for X and Medium based on my product brief.` |
| **Draft from materials** | Agent Chat | `Draft the X thread and Medium article for the first planned item in workspace/content-calendar.csv.` |
| **Ask what to do today** | Agent Chat | `What should I work on today? Give me the top 1–3 actions from current workspace state.` |
| **Confirm publication** | Agent Chat | `Record that "Your Post Title" on X was published today with URL https://...` |
| **Import CSV / XLSX stats** | Agent Chat | `Import the attached local performance CSV/XLSX and refresh dashboard.html.` |
| **Weekly retrospective** | Agent Chat | `Review last week's recorded results and recommend what to repeat or adjust next week.` |
| **Preview live board** | File Tree | Click `dashboard.html` (supports Table/Board toggle, platform filter, search, and 1-click prompt copy) |

---

## Workflow & Data Boundaries

**Input → Plan → Draft → Track Publishing → Import Results → Review → Update Next Plan**

To keep your operational records trustworthy, this workspace enforces strict truth rules (defined in `AGENTS.md` and `PLAYBOOK.md`):

- **No fake publishing:** A draft is never treated as `Published`, and a `Scheduled` item never becomes `Published` just because its date passed—only your explicit confirmation updates it.
- **No fabricated metrics:** Missing metrics always display as `N/A` (never `0`), and cumulative snapshots are shown by date rather than summed together.
- **No silent overwrites:** Existing drafts, calendar rows, and performance history are preserved across updates.
- **100% local-first:** This template does not connect social accounts, auto-post, scrape URLs, or call third-party APIs.

---

## Workspace Structure

```text
.
├── dashboard.html                 # Interactive visual dashboard (Preview directly in HTML view)
├── README.md                      # Quickstart guide & prompt cheat sheet
├── PLAYBOOK.md                    # 7-step content operations SOP
├── AGENTS.md / CLAUDE.md          # Agent governance, truth rules & validation workflow
├── HANDOFF.md                     # Session-to-session continuity log
├── workspace/
│   ├── brand-context.md           # Durable brand facts, audience, tone & exclusions
│   ├── content-calendar.csv       # Platform-specific content schedule & status
│   ├── performance.csv            # Observed metrics with source traceability
│   ├── drafts/                    # Readable Markdown drafts linked from the calendar
│   └── materials/                 # User-authorized local reference materials
├── scripts/                       # Local validation, XLSX/CSV import & HTML renderer
└── tests/                         # Automated acceptance & regression test suite
```

---

## License

Released under the [MIT License](./LICENSE).
