# Reverse-Engineered ATS Job Tracker

> **Status:** Work in progress — actively adding better filtering, scoring, and dashboards.

This project is a **Reverse-Engineered ATS Job Tracker**.

It continuously pulls job postings from multiple ATS providers  
(e.g. **Workday, Greenhouse, Lever, Ashby, SmartRecruiters**), normalizes them into a unified schema,  
filters to **US / US-remote ML/AI/Data/Backend/Infra roles**, and stores **daily snapshots per company**.

On top of snapshots, it computes **diffs over time** (Added / Removed / Changed jobs) to enable hiring trend analytics.

![Overview](images/overview.png)

---

## High-level goals

- Track how individual companies hire over time, not just point-in-time openings.
- Provide a single unified representation from different ATS backends.
- Maintain daily history supporting:
  - US hiring velocity.
  - Role mix trends (AI / ML / Data / Backend / Infra).
  - Seniority momentum (how much of the funnel is junior/mid/senior).
  - Time-to-close estimation from first_seen / last_seen.

---

## Current capabilities

1. **Multi‑ATS ingestion**
   - Fetch raw jobs from ATS APIs / endpoints:
     - Workday, Greenhouse, Lever, Ashby, SmartRecruiters.
2. **Normalization into one schema**
   - Map provider‑specific fields into a common job record:
     - `company_slug`, `title`, `team`, `location`, `remote_flag`, `seniority`, `job_id`, `url`, timestamps, etc.
3. **Filtering to “my” target set**
   - US‑eligible / US‑remote roles only.
   - ML / AI / Data / Backend / Infra‑type titles using keyword + rules around seniority and noise words.
4. **Snapshotting per company per run**
   - Store **raw**, **filtered**, and **diff** snapshots for each company in each run.
5. **Diffs over time**
   - Compute **Added / Removed / Changed** jobs vs. the last snapshot for that company.
   - Maintain `first_seen` / `last_seen` to support time‑to‑close analysis.
6. **Exactly one file per type per run**
   - For each company and run:
     - one raw file,
     - one filtered file,
     - one diff file.

---

## Dashboard: Momentum Board

The Streamlit dashboard is designed to answer, immediately:

- Which companies have meaningful momentum this week (booming/freezing/volatile/stable) and why
- What that implies for timing (apply-window vs networking trigger)
- How long roles typically last per company (lifespan / durability)
- The global market pulse (open roles, net change, mix shifts, concentration)

Run it:

```powershell
.\.venv\Scripts\python -m streamlit run dashboard\Overview.py
```

If you have historical snapshots but no signals yet, you can backfill:

```powershell
.\.venv\Scripts\python scripts\backfill_analytics.py
```

---

## Architecture & Data Flow

At a high level, the tracker is a batch pipeline:

1. **Company & ATS config**
   - Static configuration for each company: ATS type, base endpoint, filters, slugs.
2. **Fetch jobs (per company)**
   - Call the underlying ATS API with pagination and basic parameters (e.g., limit/offset for Workday).
   - Collect all open jobs into a raw list.
3. **Normalize & annotate**
   - Convert raw objects into a unified schema.
   - Derive fields like `seniority_level`, `is_remote`, `us_eligible` using rule‑based classification.
4. **Filter to target roles**
   - Keep only jobs in the target geography (US / US‑remote) and target role families (ML/AI/Data/Backend/Infra).
5. **Snapshot writer**
   - Write **raw** and **filtered** snapshots for each company.
   - Use consistent file naming including date/time and `company_slug` so runs are easy to diff and backfill.
6. **Diff engine**
   - For each company, compare the latest filtered snapshot to the previous one:
     - new jobs (`Added`),
     - closed/removed jobs (`Removed`),
     - changed jobs (`Changed` — e.g., title/location/seniority changes).
7. **Analytics hooks**
   - Downstream consumers can read snapshots and diffs to compute hiring velocity, role mix, and time‑to‑close.

A simplified text view:

```text
Config (companies + ATS type)
        ↓
Ingestion (per ATS client)
        ↓
Normalization & annotation
        ↓
Filtering (US + role family)
        ↓
Snapshots (raw + filtered)
        ↓
Diff engine (Added / Removed / Changed)
        ↓
Analytics / dashboards (work in progress)
```

---

## Data model & files

Key concepts:

- **Raw snapshot**
  - All normalized jobs for a company for a given run.
  - Preserves as much provider context as possible.
- **Filtered snapshot**
  - Subset of jobs that pass **US‑eligibility** and **role family** filters.
  - Used by downstream analytics and diffing.
- **Diff**
  - Comparison between consecutive filtered snapshots for a given company.
  - Contains lists of `added`, `removed`, and `changed` job IDs and their metadata.
- **US‑eligible**
  - Explicit US markers (`United States`, `US`, state abbreviations).
  - Remote roles that do **not** contain region hints that clearly exclude the US (e.g., “Europe only”, “APAC only”).
- **First seen / last seen**
  - `first_seen`: when a job first appears in filtered snapshots.
  - `last_seen`: last run where the job was still present.
  - Together they approximate **time‑to‑close**.

File layout is designed so each run is deterministic and easy to inspect. A typical structure looks like:

```text
data/
  raw/
    2025-01-10/
      company_a_raw.jsonl
      company_b_raw.jsonl
  filtered/
    2025-01-10/
      company_a_filtered.jsonl
      company_b_filtered.jsonl
  diffs/
    2025-01-10/
      company_a_diff.jsonl
      company_b_diff.jsonl
```

*(Exact paths and filenames may differ slightly from this example, but the one‑raw / one‑filtered / one‑diff per company per run contract is enforced.)*

---

## Performance, Latency & Metrics

This is a **batch** job rather than an online API, so “latency” refers to **per‑run** and **per‑company** times rather than single user requests.

### Runtime and scale

Main contributors:

- **Network latency** to each ATS API (especially for paginated providers like Workday).
- **JSON processing**: parsing large responses and normalizing them.
- **I/O**: writing snapshots and diffs to disk.

As the number of tracked companies increases, total runtime scales roughly linearly with:

- number of companies ×
- pages per company ×
- jobs per page.

For observability, the tracker is organized so you can easily log and track:

- time per **company fetch** (ingestion),
- time per **normalization + filtering** pass,
- time per **diff computation**.

### Cost and quotas

There is no LLM in the core tracker, so “cost per run” is mainly about:

- ATS rate limits and quotas,
- total number of HTTP calls,
- storage used by snapshots and diffs.

Tracking per‑company counts (jobs fetched, jobs kept, jobs added/removed) and per‑run HTTP error rates gives a good picture of both **coverage** and **stability**.

### Evaluation & quality metrics

Useful metrics and checks:

- **Coverage per company**:
  - total jobs fetched vs. jobs visible on the public careers site.
- **Filter quality**:
  - percentage of fetched jobs that pass the US + role family filters.
  - spot‑check false positives / false negatives by company.
- **Diff sanity**:
  - number of added/removed jobs per run (extreme spikes or zeros can indicate ingestion issues).
- **Time‑to‑close estimates**:
  - distribution of `(last_seen - first_seen)` durations for jobs by company and role family.

These can be computed from snapshots and diffs without any extra tooling.

---

## Infrastructure & Ops Notes

The tracker is intentionally light on infrastructure requirements:

- **Execution model**
  - Can be run as a local Python script, a scheduled container, or a cron job on a VM.
- **Configuration**
  - Company list, ATS types, and filters are driven by config and environment variables.
- **Storage**
  - Snapshots and diffs are plain files on disk, which can be:
    - kept locally, or
    - synced to object storage (e.g., S3/GCS) for backups and dashboards.
- **Logging**
  - Each run can log:
    - start/end timestamps,
    - per‑company job counts,
    - per‑company runtime,
    - HTTP errors or parsing failures.

These patterns are enough to support monitoring and debugging while the project continues to evolve.

---

## Key concepts (summary)

- **Raw snapshot**: all normalized jobs.
- **Filtered snapshot**: US / US‑remote, relevant technical roles.
- **Diff**: comparison between consecutive snapshots.
- **US‑eligible**: explicit US evidence or remote without non‑US region markers.
- **First seen / last seen**: used for time‑to‑close.

---

## Example Postmortem: Non‑US Roles Leaking into “US‑Only” Filter

**Symptom**  
Some clearly non‑US roles (e.g., “Software Engineer – Berlin” or “Data Scientist – London”) appeared in the filtered US / US‑remote set.

**Investigation**

- Sampled filtered snapshots where `location` contained obvious non‑US cities.
- Noticed several job titles with mixed markers (e.g., “Remote – EMEA / US” and “Remote, Europe or US”) being treated as US‑eligible.
- Found cases where remote jobs with only regional hints (e.g., “Remote – Europe”) were incorrectly passing the filter because they were classified as “remote” with no strong negative region signal.

**Root cause**

- The **US‑eligibility** logic relied mainly on positive US markers and a simple remote flag.
- There were not enough explicit negative checks for non‑US regions (e.g., `Europe`, `EMEA`, `APAC`, `Canada`, explicit country lists).
- Mixed labels (“US or Europe”) were not being treated separately from “US only”.

**Fix**

- Expanded the location parser to:
  - detect and tag **regional hints** (Europe/EMEA/APAC/Canada/etc.), and
  - treat “remote” without any US markers but with clear non‑US region hints as **non‑US‑eligible**.
- Added a special case for mixed labels:
  - when a job is “US or non‑US region” and the location string is ambiguous, mark it as **“maybe US”** and keep it in a separate bucket instead of the main US‑only set.
- Re‑ran the tracker on recent days and verified that clearly non‑US roles no longer appeared in the US‑only filtered snapshots.

This kind of postmortem is used to tighten the heuristics over time while keeping the pipeline simple and deterministic.

---

## Future scope (still working on it)

This project is still actively evolving. Planned and in‑progress work includes:

- **Hiring velocity dashboards**
  - Per‑company and per‑role family view of added/removed jobs over time.
- **Role mix and seniority trends**
  - How much of a company’s funnel is junior vs. mid vs. senior, and how it shifts over time.
- **Time‑to‑close analytics**
  - More robust analysis of `first_seen` / `last_seen` distributions, including outliers.
- **Company news/funding overlays**
  - Join job trends with public company events (funding rounds, layoffs, big launches).
- **Relevance scoring for “my” profile**
  - Score roles per company based on skills/stack and hide clearly off‑target roles.
- **Better diff & trend visualization**
  - A small UI or notebook layer to explore diffs interactively.
