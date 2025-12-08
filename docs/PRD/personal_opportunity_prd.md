# PRD – “Personal Opportunity View” for RE-ATS Dashboard

## 0. Context / framing for the LLM

This project is a **Reverse-Engineered ATS Job Tracker**.

- **Input data**:
  - Jobs: stored as JSON snapshots and per-company diff files (Added/Removed/Changed).
  - Aggregated job metrics: `job_diffs_daily` table in SQLite (one row per `company_slug, date` with counts).
  - News: `normalized_news` and an aggregated `company_news_daily` table in the same SQLite DB.

- **Existing dashboard (Streamlit)**:
  - Overview page: generic metrics (total added, leaderboard, simple trends).
  - Company Detail page: basic per-company stats & charts.
  - Diff Viewer page: shows raw Added/Removed/Changed jobs for a chosen company/date.
  - Role Explorer page: generic search on recent added jobs.

The goal of this PRD is to **shift the dashboard from generic reporting to a personal opportunity radar** for one user (Krishna), using only existing data + derived scores.  

**Important constraint**:  
The dashboard must **never run job or news scrapers**. It should **only read** from SQLite and existing JSON files.

---

## 1. Overall goals

1. Help the user answer:  
   **“Which companies and roles deserve my energy this week?”**
2. Turn raw metrics and news into:
   - **Company-level signals**: hiring momentum, opportunity score, news context.
   - **Role-level signals**: match score vs user’s profile.
3. Provide a **lightweight weekly “playbook”** summarizing where to focus.
4. Keep existing raw views accessible but **de-emphasized**; prioritize new personalized views.

Non-goals (for now):

- No ML forecasting / time-series prediction.
- No multi-user support or authentication.
- No triggering of scraping pipelines from the UI.

---

## 2. Core concept: “My Fit” profile (used across features)

Introduce a **user profile object** (in code/config, not through UI yet) that encodes Krishna’s preferences:

- `target_keywords`: list of title keywords that indicate good fit  
  (e.g., “machine learning”, “ml engineer”, “llm”, “nlp”, “agentic”, “infra”, “platform”, “rag”, etc.)
- `avoid_keywords`: list to downweight or avoid (e.g., “manager”, “director”, “vp”).
- `seniority_preference`:
  - **Mid-level > Senior > Junior/Intern**  
  - Mid/unspecified titles should get **more score** than senior titles.
- `location_preference`:
  - Preferred cities/regions (e.g., SF Bay, NYC, Seattle, Austin).
  - US-remote is okay but not the primary driver.
- (Optional) `company_priority_tiers` for later (dream / strong / okay).

This profile must be:

- **Readable** and easy to tweak.
- **Used consistently** in:
  - Company Opportunity Score.
  - Role match scoring.
  - Diff Viewer highlighting.

---

## 3. Feature A – “My Opportunity Board” (Overview top section)

### Purpose

Replace the generic leaderboard on the Overview page with a **personalized ranking of companies** based on how promising they are for Krishna, over a recent time window (default 14 days, with options 7/30).

### Functionality

1. For each company:
   - Aggregate `job_diffs_daily` over the selected window:
     - `added_total`, `removed_total`, `net_change`, `senior_plus_added_count`.
   - Derive `mid_or_unspecified_added = added_total - senior_plus_added_count`.
   - Aggregate `company_news_daily`:
     - counts for `funding`, `ai_announcement`, `product`, `layoff`, `earnings`.
2. Compute a **Company Opportunity Score** with these rules:
   - Mid-level/unspecified additions contribute **more** than senior additions.
   - Funding + AI/product events increase score.
   - Layoff events decrease score.
   - Positive net hiring increases score.
   - Exact numeric weights should be simple and documented in comments, not magic.
3. Classify companies based on score and recent trend:
   - `🔥 Hot`, `🙂 Warming`, `😐 Flat`, `🧊 Cooling/Cold`.
4. UI:
   - At the top of Overview, show a **grid/list of top 5–10 companies** sorted by Opportunity Score.
   - Each card includes:
     - Company name.
     - Momentum label + score.
     - Last N days stats: `added_total`, `net_change`, `mid_or_unspecified_added`, `senior_plus_added_count`.
     - News badges: chips for `funding`, `ai`, `earnings`, `layoffs` if present.
     - A short text hint derived from data (e.g., “Strong mid-level hiring + recent funding.”).
   - Existing generic leaderboard and trend chart should be moved **below** this as an “Advanced metrics” section (optionally in an expander).

### Acceptance criteria

- Overview loads without errors using only existing SQLite data.
- Top section clearly shows Opportunity cards; raw leaderboard is secondary.
- Score & labels are straightforward and documented (e.g., in comments / docstring).

---

## 4. Feature B – Personalized Role Explorer

### Purpose

Transform Role Explorer from generic search into a **ranked list of roles ordered by personal match**, on top of already filtered jobs.

### Functionality

1. Focus on **added jobs** in a given time window (default 7 or 14 days).
2. For each added job, compute a **Role Match Score** using:
   - Title matches against `target_keywords` (positive increments).
   - Title matches against `avoid_keywords` (negative increments).
   - Seniority:
     - Mid-level/unspecified (no “senior/principal/staff/director” etc.) → highest bonus.
     - Senior → smaller bonus.
     - Intern/Junior → penalty or very low score.
   - Location:
     - Preferred cities/regions → positive bonus.
     - US-remote → smaller positive bonus.
   - Recency:
     - Jobs added in last 3 days → extra bonus.
     - Jobs older in the window → lower bonus.
3. Map score to **match labels**:
   - Strong / Good / Okay / Weak.
4. UI changes:
   - Default filters:
     - Time range: 7 or 14 days.
     - Only show Strong + Good by default (toggle to show all).
   - Layout:
     - “Spotlight Roles (Top N)” list at top, sorted by match score.
     - Full table below sorted by match score, with:
       - Date added, company, title, locations, match label, link.
       - Optionally a small text like “Matched on: ML, LLM, SF Bay”.
   - Existing free-text search and company filter can stay, but should refine within this ranked set.

### Acceptance criteria

- Role Explorer returns roles even if the user doesn’t type anything (it should show top matches by default).
- Strong/Good labels visibly cluster jobs that look good for Krishna.
- Behavior is stable when the window has few or no jobs.

---

## 5. Feature C – Enhanced Company Detail & Navigation

### Purpose

Make the Company Detail page tell a **clear story of momentum + news** for the selected company and support easy navigation across many companies.

### Functionality

1. For selected company + time window (7/30/90 days):
   - Aggregate current window metrics (`total_added`, `total_removed`, `net_change`).
   - Aggregate previous window metrics (same length just before this period) to compare.
   - Classify momentum: Hot / Warming / Cooling / Flat using simple rules based on `total_added`, `net_change`, and comparison with previous window.
2. Show at top:
   - Momentum label (with icon).
   - 2–3 bullet sentences summarizing:
     - “Added X roles (Y mid-level) and removed Z in the last N days.”
     - “Compared to previous N days: +/- change.”
     - “News: funding/ai/earnings/layoffs in the period.”
3. Timeline chart:
   - Daily bars for `added_count` and `removed_count`.
   - Overlay markers for days with `has_major_event` from `company_news_daily`.
   - Tooltip should show event types and top headline.
4. Navigation improvements:
   - Company selector should support **typeahead search**.
   - Add concept of **favorites**:
     - Allow the user to star/unstar companies (persisted in a simple config or JSON).
     - In the selector, list favorites at the top.
   - From Opportunity Board cards, there should be a way to navigate directly to this page with the company preselected.
   - Optional: Next/Previous company buttons based on sorted Opportunity Board order.

### Acceptance criteria

- Company Detail loads for any tracked company and shows momentum + chart + news.
- Selecting a company from Opportunity Board correctly opens Company Detail with that company selected.
- Navigation is usable even with ~50 companies.

---

## 6. Feature D – Spike-driven Diff Viewer

### Purpose

Use Diff Viewer as a way to inspect **interesting spike days** and see which added jobs are good matches, not as a generic diff dump.

### Functionality

1. Entry points:
   - From Company Detail:
     - Identify the day in the current range with maximum `added_count`.
     - Show a prominent link/button: “Inspect spike on <date> (N jobs added)” which opens Diff Viewer prefilled with that company & date.
   - Keep existing manual selection for company/date as backup.
2. In Diff Viewer:
   - Always show top summary cards for added/removed/changed & Senior+ added.
   - Default tab: **Added**.
   - For Added jobs:
     - Reuse Role Match Score from Feature B.
     - Sort by match score; default view shows Strong + Good first.
     - Provide toggles:
       - “Show only Strong/Good”
       - “Show All”
     - Cards should show title, company (redundant but fine), locations, match label, link, and why it matched (keywords/locations).
   - Removed & Changed tabs can remain but are secondary.
3. News context:
   - For the selected date, show relevant news from `company_news_daily` or `normalized_news`:
     - Event types.
     - 1–3 headlines with links.

### Acceptance criteria

- Spike button on Company Detail accurately jumps into Diff Viewer.
- Diff Viewer defaults to Added tab and shows match labels.
- Strong/Good/Okay classification mirrors Role Explorer.

---

## 7. Feature E – Weekly Playbook

### Purpose

Provide a **one-glance plan for the current week**, based on opportunity scores & roles.

### Functionality

Over the last 7 days:

1. Compute:
   - Top 3 companies by Opportunity Score → “Priority companies”.
   - Next 2–3 companies with major news but lesser hiring → “Watchlist”.
   - Number of Strong + Good match roles from Role Explorer logic.
   - Biggest spike day: `(company_slug, date)` with max `added_count`.
2. UI:
   - On Overview page, add a “This Week’s Playbook” panel near the top (below My Opportunity Board).
   - Content example:
     - Priority Companies: [A, B, C] with short reason text.
     - Watchlist: [D, E] with reason text (e.g., “recent funding but hiring flat so far”).
     - “New roles matching you: N (X Strong, Y Good)” with link to Role Explorer (pre-filtered to 7 days).
     - “Biggest spike: <company> on <date> (+M roles)” with link to spike in Diff Viewer.
3. Optional: Provide a small “Copy as text” helper (not required), but make sure the content is concise and readable as is.

### Acceptance criteria

- Weekly Playbook updates as new diffs/news are ingested and ETL runs.
- Numbers and company names in the Playbook correspond to underlying data.
- Links to Role Explorer and Diff Viewer navigate with appropriate filters preselected.

---

## 8. De-emphasizing old views (without deleting them)

- Keep:
  - Raw leaderboard table.
  - Cross-company hiring trend chart.
  - Full Added/Removed/Changed sections in Diff Viewer.
- But:
  - Move them **below** new sections or inside `st.expander` or similar.
  - Label them clearly as “Advanced / Raw view”.
- Ensure all new features (Opportunity Board, Playbook, match-based views) are **above the fold** and the default user experience.

---

## 9. General implementation notes for the LLM

- Do **not** trigger or import any code that runs scrapers (job/news ingestion). Dashboard is **read-only**.
- Keep all scoring functions:
  - Pure, deterministic, and cheap (no external API calls).
  - With clear docstrings explaining logic and parameters, so they’re easy to tune later.
- Try to centralize:
  - Company Opportunity Score logic in one helper.
  - Role Match Score logic in one helper.
- Respect existing project structure:
  - Reuse `data_access` or equivalent module for SQLite/JSON reads.
  - Implement UI changes inside existing Streamlit page files (`Overview`, `Company Detail`, `Diff Viewer`, `Role Explorer`).
- Add short in-code comments tying each new feature back to this PRD (e.g., `# Feature A: My Opportunity Board`).

