# Reverse-Engineered ATS Job Tracker

This project is a **Reverse-Engineered ATS Job Tracker**.  
It continuously pulls job postings from multiple ATS providers, normalizes them into a unified format, filters down to **US + US-remote, ML/AI/Data/Backend/Infra roles**, and stores **daily snapshots per company**.  
On top of snapshots, it computes **diffs over time** (Added / Removed / Changed jobs) to enable hiring trend analytics.

## High-level goals

- Track how individual companies hire over time.
- Provide a single unified representation from different ATS.
- Maintain daily history supporting:
  - US hiring velocity.
  - Role mix trends.
  - Seniority momentum.
  - Time-to-close.

## Current capabilities

1. Fetch raw jobs from ATS (Workday, Greenhouse, Lever, Ashby, SmartRecruiters).
2. Normalize all jobs into one unified format.
3. Filter to US / US-remote ML/AI/Data/Backend/Infra roles.
4. Store raw + filtered snapshots per company per run.
5. Compute diffs (Added / Removed / Changed).
6. Save exactly one raw, one filtered, one diff file per company per run.

## Key concepts

- **Raw snapshot**: all normalized jobs.
- **Filtered snapshot**: US / US-remote, relevant technical roles.
- **Diff**: comparison between consecutive snapshots.
- **US-eligible**: explicit US evidence or remote without non-US region markers.
- **First seen / last seen** timestamps: used for time-to-close.

## Future scope

- Hiring velocity dashboards.
- Role mix and seniority trends.
- Time-to-close analytics.
- Company news/funding overlays.
