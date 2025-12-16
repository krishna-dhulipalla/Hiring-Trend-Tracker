import json
import random
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

from src.utils import parse_location

META_GRAPHQL_URL = "https://www.metacareers.com/graphql"


def _strip_for_while(text: str) -> str:
    t = text.strip()
    if t.startswith("for (;;);"):
        t = t[len("for (;;);") :].lstrip()
    return t


def _to_base36(n: int) -> str:
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    if n == 0:
        return "0"
    out = []
    while n:
        n, r = divmod(n, 36)
        out.append(chars[r])
    return "".join(reversed(out))


def _parse_items_and_page_info(data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    root = data.get("data", {}).get("job_search_with_featured_jobs")
    if not isinstance(root, dict):
        return [], {}

    all_jobs = root.get("all_jobs")
    items: List[Dict[str, Any]] = []
    page_info: Dict[str, Any] = {}

    if isinstance(all_jobs, dict):
        nodes = all_jobs.get("all_jobs") or all_jobs.get("nodes") or []
        if isinstance(nodes, list):
            items = [x for x in nodes if isinstance(x, dict)]
        page_info = all_jobs.get("page_info") or {}

        if not items:
            nested = all_jobs.get("all_jobs")
            if isinstance(nested, dict):
                nodes2 = nested.get("all_jobs") or nested.get("nodes") or []
                if isinstance(nodes2, list):
                    items = [x for x in nodes2 if isinstance(x, dict)]
                page_info = nested.get("page_info") or page_info

    elif isinstance(all_jobs, list):
        items = [x for x in all_jobs if isinstance(x, dict)]

    return items, page_info if isinstance(page_info, dict) else {}


def fetch_jobs(config: Dict[str, Any], max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Requires:
      - config["payload"] : dict of DevTools Form Data
      - config["cookie"]  : Cookie header copied from DevTools Request Headers (critical)
    Optional:
      - config["x_asbd_id"] : value of X-ASBD-ID header from DevTools (often helps)
    """
    payload = dict(config.get("payload") or {})
    if not payload:
        raise ValueError("config['payload'] is required (DevTools Form Data as dict).")

    cookie = (config.get("cookie") or "").strip()
    if not cookie:
        raise RuntimeError(
            "Meta /graphql is returning an HTML error page because this request lacks browser context.\n"
            "Fix: copy the *Cookie* header from the working DevTools /graphql request and paste it into run_meta.py."
        )

    user_agent = config.get(
        "user_agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )

    variables_raw = payload.get("variables", "{}")
    variables = json.loads(variables_raw) if isinstance(variables_raw, str) else dict(variables_raw)
    variables.setdefault("search_input", {})

    rpp = config.get("results_per_page") or variables["search_input"].get("results_per_page") or 50
    # variables["search_input"]["results_per_page"] = rpp # This seems to cause noncoercible error

    session = requests.Session()

    headers = {
        "User-Agent": user_agent,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://www.metacareers.com",
        "Referer": "https://www.metacareers.com/jobsearch",
        "X-FB-LSD": str(payload.get("lsd", "")),
        # CRITICAL:
        "Cookie": cookie,
        # Helps look more like browser:
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
    }

    x_asbd_id = (config.get("x_asbd_id") or "").strip()
    if x_asbd_id:
        headers["X-ASBD-ID"] = x_asbd_id

    all_jobs_out: List[Dict[str, Any]] = []
    page_count = 0
    end_cursor: Optional[str] = None
    has_next = True

    req_counter = payload.get("__req", "1")
    try:
        req_int = int(str(req_counter), 36) if isinstance(req_counter, str) else int(req_counter)
    except Exception:
        req_int = 1

    SAFE_MAX_PAGES = 2000
    seen_ids = set()
    seen_page_signatures = set()

    while has_next:
        if max_pages and page_count >= max_pages:
            break
        if page_count >= SAFE_MAX_PAGES:
            print(f"Reached safe limit {SAFE_MAX_PAGES}. Stopping.")
            break

        page_count += 1
        print(f"Fetching Meta page {page_count}...")

        if end_cursor:
            variables["search_input"]["after"] = end_cursor

        req_int += 1
        payload["__req"] = _to_base36(req_int)
        payload["variables"] = json.dumps(variables, separators=(",", ":"))

        resp = session.post(META_GRAPHQL_URL, data=payload, headers=headers, timeout=30)

        if resp.status_code != 200:
            print(f"Error: HTTP {resp.status_code}")
            # print("Body preview:", resp.text[:900])
            break

        try:
            data = json.loads(_strip_for_while(resp.text))
        except Exception as e:
            print(f"JSON Parse Error: {e}")
            break

        if "errors" in data:
            print("GraphQL errors:", data["errors"])

        items, page_info = _parse_items_and_page_info(data)
        if not items:
            print("No items in response. Stopping.")
            break

        # Duplicate Page Check
        current_page_ids = [str(item.get("id")) for item in items]
        page_sig = tuple(current_page_ids)
        if page_sig in seen_page_signatures:
            print(f"Duplicate page signature on page {page_count}. Stopping.")
            break
        seen_page_signatures.add(page_sig)
        
        new_jobs_on_page = 0
        for item in items:
            job_id = item.get("id")
            
            if job_id not in seen_ids:
                seen_ids.add(job_id)
                new_jobs_on_page += 1

            title = item.get("title")

            loc_raw = item.get("locations") or []
            loc_strings: List[str] = []
            for l in loc_raw:
                if isinstance(l, str):
                    loc_strings.append(l)
                elif isinstance(l, dict):
                    loc_strings.append(l.get("city") or l.get("name") or str(l))

            parsed_locs = [parse_location(l) for l in loc_strings]
            teams = item.get("teams") or []
            sub_teams = item.get("sub_teams") or []

            all_jobs_out.append(
                {
                    "job_id": job_id,
                    "title": title,
                    "company": "Meta",
                    "locations": parsed_locs,
                    # per your request: unchanged
                    "url": f"https://www.metacareers.com/jobs/{job_id}/",
                    "employment_type": None,
                    "posted_date": None,
                    "remote_status": None,
                    "description_raw": None,
                    "department": teams[0] if teams else None,
                    "team": teams,
                    "sub_teams": sub_teams,
                    "source": "meta",
                    "fetched_at": None,
                }
            )
            
        if new_jobs_on_page == 0:
            print(f"Page {page_count} returned {len(items)} items but all were seen before. Stopping.")
            break

        has_next = bool(page_info.get("has_next_page", False))
        end_cursor = page_info.get("end_cursor")

        if has_next and not end_cursor:
            print("has_next_page=true but end_cursor missing; stopping to avoid infinite loop.")
            break

        time.sleep(random.uniform(1, 2))

    return all_jobs_out
