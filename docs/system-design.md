# System Design Overview

This describes the ATS Job Tracker end-to-end in conceptual steps.

## 1. Ingestion Layer

Fetch all open jobs per company from its ATS:
- Workday (pagination quirks handled via empty-page, repeated-page, and total caps)
- Greenhouse
- Lever
- Ashby
- SmartRecruiters

Output: raw ATS jobs.

## 2. Normalization Layer

Convert raw jobs to unified representation:
- Stable identity (`job_key`)
- Title, req id, URL
- Locations[] (parsed for is_us, is_remote)
- Posted date (best-effort)
- First_seen / last_seen
- Seniority & discipline tags

Output: normalized jobs.

## 3. Filtering Layer

Two filters:

### Location Filter
- Accept US + US-remote.
- Reject non-US or non-US-remote (“Remote Spain”, “Remote EMEA”).

### Role Relevance
- Accept ML/AI/Data/Backend/Infra.
- Reject Sales, HR, Legal, Support, etc.

Output: filtered snapshot.

## 4. Snapshot & Diff Layer

Each run per company produces:
- Raw snapshot file
- Filtered snapshot file

Diff compares current vs previous filtered snapshot:
- Added: new job_keys
- Removed: disappeared job_keys
- Changed: meaningful field differences:
  - Title
  - Locations / remote flags
  - Status
  - Posted_at (only null → non-null)

Diff file contains:
- Summary (added, removed, changed, us_added, us_remote_added, senior_plus_added)
- Arrays of diff cards.

## 5. Analytics Foundation

With snapshots + diffs, system can compute:
- US hiring velocity
- Role mix over time
- Seniority momentum
- Time-to-close
- Future: correlate with company news and funding events.
