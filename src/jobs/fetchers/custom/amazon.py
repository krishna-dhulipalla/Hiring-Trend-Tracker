
import requests
import time
import random
from src.utils import parse_location, parse_posted_at

def fetch_jobs(config, max_pages=None):
    """
    Fetches jobs from Amazon Jobs.
    max_pages: Optional int limit.
    """
    base_params = config.get("params", {})
    if "result_limit" not in base_params:
        base_params["result_limit"] = 50
    if "offset" not in base_params:
        base_params["offset"] = 0
        
    offset = base_params["offset"]
    limit = base_params["result_limit"]
    
    all_jobs = []
    page_count = 0
    url = "https://www.amazon.jobs/en/search.json"
    
    SAFE_MAX_PAGES = 2000
    seen_ids = set()
    seen_page_signatures = set()
    
    while True:
        # 1. Safety Checks
        if max_pages and page_count >= max_pages:
            print(f"Reached max_pages {max_pages}. Stopping.")
            break
        if page_count >= SAFE_MAX_PAGES:
            print(f"Reached safe limit {SAFE_MAX_PAGES}. Stopping.")
            break
            
        page_count += 1
        print(f"Fetching Amazon offset {offset}...")
        
        current_params = base_params.copy()
        current_params["offset"] = offset
        
        try:
            resp = requests.get(url, params=current_params)
            if resp.status_code in [429, 500, 502, 503, 504]:
                print(f"Got {resp.status_code}, backing off...")
                time.sleep(random.uniform(5, 10))
                continue
                
            resp.raise_for_status()
            data = resp.json()
            
            jobs_list = data.get("jobs", [])
            hits = data.get("hits", 0)
            
            if not jobs_list:
                print("No jobs returned. Stopping.")
                break
            
            # 2. Duplicate Page Check
            current_page_ids = [str(item.get("id_icims") or item.get("id")) for item in jobs_list]
            page_sig = tuple(current_page_ids)
            if page_sig in seen_page_signatures:
                print(f"Duplicate page signature at offset {offset}. API looping. Stopping.")
                break
            seen_page_signatures.add(page_sig)

            # 3. New Jobs Check
            new_jobs_on_page = 0
            for item in jobs_list:
                job_id = str(item.get("id_icims") or item.get("id"))
                
                if job_id not in seen_ids:
                    seen_ids.add(job_id)
                    new_jobs_on_page += 1

                title = item.get("title")
                
                locs = []
                if "locations" in item and isinstance(item["locations"], list):
                     locs = item["locations"]
                elif "location" in item:
                     locs = [item["location"]]
                else:
                     city = item.get("city")
                     state = item.get("state")
                     country = item.get("country_code")
                     parts = [p for p in [city, state, country] if p]
                     if parts:
                         locs = [", ".join(parts)]
                
                parsed_locs = [parse_location(l) for l in locs]
                
                job_path = item.get("job_path")
                item_url = f"https://www.amazon.jobs{job_path}" if job_path else None
                posted_date = parse_posted_at(item.get("posted_date"))
                
                job = {
                    "job_id": job_id,
                    "title": title,
                    "company": "Amazon",
                    "locations": parsed_locs,
                    "url": item_url,
                    "employment_type": item.get("schedule_type_id"),
                    "posted_date": posted_date,
                    "remote_status": None,
                    "description_raw": item.get("description"),
                    "department": item.get("job_category"),
                    "team": item.get("team"),
                    "sub_teams": None,
                    "source": "amazon",
                    "fetched_at": None
                }
                all_jobs.append(job)
            
            if new_jobs_on_page == 0:
                print(f"Offset {offset} returned {len(jobs_list)} items but all were seen before. Stopping.")
                break
                
            offset += limit
            
            if offset >= hits:
                print(f"Offset {offset} >= hits {hits}. Stopping.")
                break
                
            if len(jobs_list) < limit:
                print(f"Returned {len(jobs_list)} items < limit {limit}. Stopping.")
                break
            
            time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            print(f"Error on Amazon offset {offset}: {e}")
            break
            
    return all_jobs
