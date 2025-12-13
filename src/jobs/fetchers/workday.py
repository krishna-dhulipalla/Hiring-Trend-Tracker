import requests
import time
import json
import os
from datetime import datetime
from typing import List, Dict, Any
from src.utils import parse_location, parse_posted_at


class WorkdayAgent:
    def __init__(self):
        self.companies = self._load_companies()
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _load_companies(self) -> List[Dict[str, str]]:
        config_path = os.path.join(os.path.dirname(
            __file__), "..", "..", "config", "workday_companies.json")
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Config file not found at {config_path}")
            return []

    def normalize_job(self, raw_job: Dict[str, Any], company_config: Dict[str, str]) -> Dict[str, Any]:
        """
        Normalizes a Workday job posting into the unified schema.
        """
        job_info = raw_job.get("jobPostingInfo", {})

        # If company_config is missing or None (safety check)
        if not company_config:
            # Try to return partial
            return {
                "source_ats": "workday",
                "title": raw_job.get("title", "Unknown"),
                "raw": raw_job
            }

        host = company_config["host"]
        tenant = company_config["tenant"]
        site_slug = company_config["site_slug"]

        # Handle flat structure vs nested
        if not job_info:
            # Flattened structure
            title = raw_job.get("title")
            external_path = raw_job.get("externalPath", "")
            job_url = f"https://{host}/en-US/{tenant}/{site_slug}{external_path}"
            location_raw = raw_job.get("locationsText", "")
            posted_at_raw = raw_job.get("postedOn")

            req_id = None
            if "bulletFields" in raw_job and raw_job["bulletFields"]:
                req_id = raw_job["bulletFields"][0]

            all_locations_str = [location_raw]
        else:
            # Standard structure
            title = job_info.get("title")
            external_path = job_info.get(
                "externalPath") or raw_job.get("externalPath", "")
            job_url = f"https://{host}/en-US/{tenant}/{site_slug}{external_path}"
            location_raw = job_info.get("location", "")

            additional_locations = job_info.get("additionalLocations", [])
            all_locations_str = [location_raw] + additional_locations

            req_id = job_info.get("jobReqId")
            posted_at_raw = job_info.get("postedDate")

        # Fallback for "2 Locations" or empty locations logic
        # If the primary location text looks like a count (e.g. "2 Locations"), ignore it
        # and try to extract from externalPath.
        import re

        # Helper to check if location string is just a count
        def is_numeric_location_summary(s):
            if not s:
                return False
            return re.match(r'^\d+\s+Locations?$', s, re.IGNORECASE) is not None

        final_locations = []

        # 1. Process explicit locations
        for loc in all_locations_str:
            if loc and not is_numeric_location_summary(loc):
                final_locations.append(loc)

        # 2. If no valid locations found (or only numeric summary), try URL extraction
        # URL format usually: /job/San-Jose-CA/Title...
        # We extract "San-Jose-CA"
        if not final_locations and external_path:
            # Regex: /job/([^/]+)/
            # or sometimes just the first segment after /job/
            # Example: /job/San-Jose-CA/Software-Engineer_R123
            match = re.search(r'/job/([^/]+)', external_path)
            if match:
                slug_loc = match.group(1)
                # Convert "San-Jose-CA" -> "San Jose CA"
                # This helps the strict parser which looks for "San Jose" or "CA"
                cleaned_loc = slug_loc.replace("-", " ")
                final_locations.append(cleaned_loc)

        parsed_locations = []
        for loc in final_locations:
            parsed_locations.append(parse_location(loc))

        # Parse Date
        posted_at = parse_posted_at(posted_at_raw)

        return {
            "source_ats": "workday",
            "company_slug": company_config["company_slug"],
            "job_key": external_path,
            "req_id": req_id,
            "title": title,
            "url": job_url,
            "locations": parsed_locations,
            "location_display": location_raw,
            "posted_at": posted_at,
            "first_seen_at": datetime.utcnow().isoformat() + "Z",
            "last_seen_at": datetime.utcnow().isoformat() + "Z",
            "status": "open"
        }

    def fetch_company_jobs(self, company: Dict[str, str], limit: int = 20) -> List[Dict]:
        """
        Robust Workday pagination:
        - Stop when page is empty (good tenants).
        - Stop when we've collected the first-page 'total'.
        - Stop when the same page repeats (tenants that ignore/loop offset).
        - De-duplicate by a stable id (jobPostingId or externalPath).
        """
        import time
        import requests

        host = company["host"]
        tenant = company["tenant"]
        site_slug = company["site_slug"]
        base_endpoint = f"/wday/cxs/{tenant}/{site_slug}/jobs"
        url = f"https://{host}{base_endpoint}"

        # Allow per-company facets if you already pass them in your config; else use empty.
        applied_facets = company.get("appliedFacets") or {}
        search_text = company.get("searchText", "")

        all_raw_jobs: List[Dict] = []
        seen_ids: set = set()               # to dedupe across pages
        seen_page_signatures: set = set()   # to detect repeating pages
        first_page_total = None

        offset = 0
        max_pages = 2000  # hard cap for safety; 2000 * 20 = 40k items worst-case

        slug = company.get("company_slug", tenant)
        print(f"[{slug}] Starting job fetch...")

        for page_idx in range(max_pages):
            payload = {
                "limit": limit,
                "offset": offset,
                "searchText": search_text,
                "appliedFacets": applied_facets,
            }

            try:
                resp = requests.post(
                    url, json=payload, headers=self.headers, timeout=20)
            except Exception as e:
                print(f"[{slug}] Request error: {e}")
                break

            # Some tenants/WAFs occasionally return non-JSON/HTML; just stop gracefully.
            try:
                data = resp.json()
            except Exception:
                # You asked to ignore non-JSON errors; stopping avoids infinite loops.
                print(
                    f"[{slug}] Non-JSON response encountered; stopping pagination.")
                break

            # Read total ONCE (page 1). Use only as a cap, not for page math.
            if first_page_total is None:
                first_page_total = data.get("total", 0)

            page = data.get("jobPostings", []) or []
            if not page:
                # (1) Normal stop condition when tenant honors offset and we're past the end.
                break

            # Build a page signature (ordered) to detect tenants that repeat the same slice.
            page_ids = []
            for j in page:
                jid = j.get("jobPostingId") or j.get("externalPath")
                # Fallback: try reqId in bulletFields when both are missing
                if not jid:
                    bf = j.get("bulletFields") or []
                    jid = bf[0] if bf else None
                page_ids.append(jid)
            page_sig = tuple(page_ids)

            if page_sig in seen_page_signatures:
                # (3) Tenant appears to be ignoring offset and returning the same page again.
                break
            seen_page_signatures.add(page_sig)

            # Append only new jobs by a stable id (same precedence as above).
            new_count = 0
            for j in page:
                jid = j.get("jobPostingId") or j.get("externalPath")
                if not jid:
                    bf = j.get("bulletFields") or []
                    jid = bf[0] if bf else None

                if jid and jid not in seen_ids:
                    seen_ids.add(jid)
                    # keep for downstream normalization
                    j["_company_config"] = company
                    all_raw_jobs.append(j)
                    new_count += 1

            # Progress print similar to your style
            if (offset == 0) or ((offset // limit) % 5 == 0):
                print(f"[{slug}] Fetched {len(seen_ids)}/{first_page_total or '?'}")

            # (2) If we’ve collected at least the first-page total, stop (caps duplicates fast)
            if first_page_total and len(seen_ids) >= first_page_total:
                break

            # If the tenant is shuffling the same items and we added nothing new, stop.
            if new_count == 0:
                break

            # Next page (even if tenant ignores it, the repeat-signature/new_count checks protect us)
            offset += limit

            # Gentle backoff to avoid hammering WAF/CDN on large boards
            time.sleep(0.1)

        return all_raw_jobs


# Module-level interface
_agent = WorkdayAgent()


def fetch_jobs(company_slug: str) -> List[Dict[str, Any]]:
    """
    Fetches jobs for a specific company slug using the WorkdayAgent.
    """
    company_config = next(
        (c for c in _agent.companies if c["company_slug"] == company_slug), None)

    if not company_config:
        print(f"No Workday config for {company_slug}")
        return []

    # Returns raw jobs with injected config
    raw_jobs = _agent.fetch_company_jobs(company_config)
    return raw_jobs


def normalize_job(raw_job):
    """
    Wrapper for normalize_job to be called by main.py
    """
    config = raw_job.get("_company_config")

    # If config not found (shouldn't happen if fetched via fetch_jobs),
    # we can try to recover or fail gracefully.

    return _agent.normalize_job(raw_job, config)
