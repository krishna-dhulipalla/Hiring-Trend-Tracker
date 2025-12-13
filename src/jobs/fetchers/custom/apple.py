"""
Apple careers fetcher (custom).

Mirrors your DevTools flow:
  1) GET /en-us/search?... to establish cookies
  2) GET /api/v1/CSRFToken to retrieve x-apple-csrf-token
  3) POST /api/v1/search with JSON body:
       {query, filters, page, locale, sort, format}

We intentionally do NOT hardcode cookies. The requests Session collects the
required ones (jobs / jssid / AWSALB... etc).
"""

from __future__ import annotations

import requests
from typing import Any, Dict, List, Optional

from src.utils import parse_location, parse_posted_at


def _bootstrap_session(
    session: requests.Session,
    search_page_url: str,
    user_agent: str,
    accept_language: str,
) -> None:
    # Establish baseline cookies (jobs/jssid/AWSALB..., geo hints, etc.)
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": accept_language,
    }
    resp = session.get(search_page_url, headers=headers, timeout=30)
    resp.raise_for_status()


def _get_csrf_token(
    session: requests.Session,
    base_url: str,
    referer: str,
    user_agent: str,
    accept_language: str,
) -> str:
    url = f"{base_url}/api/v1/CSRFToken"
    headers = {
        "User-Agent": user_agent,
        "Accept": "*/*",
        "Accept-Language": accept_language,
        "Referer": referer,
        "Origin": base_url,
    }
    resp = session.get(url, headers=headers, timeout=30)
    resp.raise_for_status()

    # Apple returns the token in a response header
    token = resp.headers.get("x-apple-csrf-token") or resp.headers.get("X-Apple-CSRF-Token")
    if not token:
        raise RuntimeError("Apple CSRFToken response did not include x-apple-csrf-token header.")
    return token


def _build_job_url(position_id: Optional[str], slug: Optional[str], team_code: Optional[str]) -> Optional[str]:
    if not position_id:
        return None
    # Matches what you saw:
    # https://jobs.apple.com/en-us/details/114438158/us-specialist-... ?team=APPST
    base = f"https://jobs.apple.com/en-us/details/{position_id}"
    if slug:
        base = f"{base}/{slug}"
    if team_code:
        base = f"{base}?team={team_code}"
    return base


def fetch_jobs(config: Dict[str, Any], max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
    base_url = config.get("base_url", "https://jobs.apple.com")

    # Important: include the location query in the bootstrap URL to align with your browser state.
    # If you want other locations later, change this URL (not cookies).
    search_page_url = config.get(
        "search_page_url",
        f"{base_url}/en-us/search?location=united-states-USA",
    )

    user_agent = config.get(
        "user_agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
    )
    accept_language = config.get("accept_language", "en-US,en;q=0.9")

    # These match your captured request body defaults
    query = config.get("query", "")
    filters = config.get("filters", {"locations": ["postLocation-USA"]})
    locale = config.get("locale", "en-us")
    sort = config.get("sort", "newest")
    fmt = config.get(
        "format",
        {"longDate": "MMMM D, YYYY", "mediumDate": "MMM D, YYYY"},
    )

    session = requests.Session()

    # 1) Bootstrap cookies
    _bootstrap_session(session, search_page_url, user_agent, accept_language)

    # 2) CSRF
    csrf_token = _get_csrf_token(session, base_url, referer=search_page_url, user_agent=user_agent, accept_language=accept_language)

    # 3) Search pages
    api_url = f"{base_url}/api/v1/search"
    headers = {
        "User-Agent": user_agent,
        "Accept": "*/*",
        "Accept-Language": accept_language,
        "Content-Type": "application/json",
        "Origin": base_url,
        "Referer": search_page_url,
        "browserlocale": locale,   # observed in your capture
        "locale": "en_US",         # observed in your capture (header). Body uses `en-us`
        "x-apple-csrf-token": csrf_token,
    }

    out: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()
    page = 0

    while True:
        page += 1
        if max_pages and page > max_pages:
            print(f"Reached max_pages {max_pages}. Stopping.")
            break
            
        print(f"Fetching Apple page {page}...")

        payload = {
            "query": query,
            "filters": filters,
            "page": page,
            "locale": locale,
            "sort": sort,
            "format": fmt,
        }

        try:
            resp = session.post(api_url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"Error fetching Apple page {page}: {e}")
            break

        res = data.get("res") or {}
        items = res.get("searchResults") or []

        if not items:
            break

        # Defensive stop in case the API starts repeating the same page forever
        page_ids = []
        for item in items:
            # Prefer stable IDs:
            # positionId is numeric, reqId is PIPE-..., id is PIPE-... too.
            position_id = str(item.get("positionId") or "").strip() or None
            req_id = str(item.get("reqId") or item.get("id") or "").strip() or None
            job_key = position_id or req_id
            if job_key:
                page_ids.append(job_key)

        # If nothing new, stop
        if page_ids and all(pid in seen_ids for pid in page_ids):
            break
        for pid in page_ids:
            seen_ids.add(pid)

        for item in items:
            position_id = str(item.get("positionId") or "").strip() or None
            req_id = str(item.get("reqId") or item.get("id") or "").strip() or None

            title = item.get("postingTitle") or item.get("title")
            slug = item.get("transformedPostingTitle")

            team = item.get("team") or {}
            team_code = team.get("teamCode") or team.get("teamID") or None

            url = _build_job_url(position_id, slug, team_code if isinstance(team_code, str) else None)

            posted_at = parse_posted_at(item.get("postDateInGMT") or item.get("postingDate"))

            # locations is a list of dicts; convert to something parse_location can handle
            locs = []
            for loc in item.get("locations") or []:
                if not isinstance(loc, dict):
                    continue
                city = (loc.get("city") or "").strip()
                state = (loc.get("stateProvince") or loc.get("state") or "").strip()
                country = (loc.get("countryName") or "").strip()
                name = (loc.get("name") or "").strip()

                # Choose the best human-readable string
                if city and state and country:
                    locs.append(f"{city}, {state}, {country}")
                elif state and country:
                    locs.append(f"{state}, {country}")
                elif name:
                    locs.append(name)
                elif country:
                    locs.append(country)

            parsed_locs = [parse_location(x) for x in locs] if locs else []

            job = {
                "adapter": "apple",
                "company": "Apple",
                "job_id": position_id or req_id,
                "req_id": req_id,
                "title": title,
                "url": url,
                "posted_at": posted_at,
                "locations": parsed_locs,
                # keep some raw fields (useful for debugging / enrichment)
                "raw": {
                    "team": team,
                    "type": item.get("type"),
                    "managedPipelineRole": item.get("managedPipelineRole"),
                    "standardWeeklyHours": item.get("standardWeeklyHours"),
                    "postExternal": item.get("postExternal"),
                },
            }
            out.append(job)

    return out