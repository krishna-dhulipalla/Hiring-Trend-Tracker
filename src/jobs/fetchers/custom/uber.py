
import requests
import time
import random
from src.utils import parse_location, parse_posted_at

def fetch_jobs(config, max_pages=None):
    """
    Fetches jobs from Uber API.
    max_pages: Optional int limit.
    """
    base_payload = config.get("payload", {})
    if "page" not in base_payload:
        base_payload["page"] = 1
    
    if "size" not in base_payload:
        base_payload["size"] = 50
        
    page = base_payload.get("page", 1)
    size = base_payload.get("size", 50)
    
    all_jobs = []
    url = "https://www.uber.com/api/loadSearchJobsResults?localeCode=en"
    
    pages_fetched = 0
    
    SAFE_MAX_PAGES = 2000
    seen_ids = set()
    seen_page_signatures = set()
    
    while True:
        # 1. Safety Limits
        if max_pages and pages_fetched >= max_pages:
             print(f"Reached max_pages {max_pages}. Stopping.")
             break
        if pages_fetched >= SAFE_MAX_PAGES:
             print(f"Reached safe limit {SAFE_MAX_PAGES}. Stopping.")
             break
             
        pages_fetched += 1
        print(f"Fetching Uber page {page}...")
        
        current_payload = base_payload.copy()
        current_payload["page"] = page
        
        # User feedback: Ensure exact payload fields.
        if "filters" not in current_payload:
            current_payload["filters"] = {}
            
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
            "x-csrf-token": "x" # Sometimes helpful to have *something*
        }
        
        try:
            resp = requests.post(url, json=current_payload, headers=headers)
            
            if resp.status_code in [429, 500, 502, 503, 504]:
                print(f"Got {resp.status_code}, backing off...")
                time.sleep(random.uniform(5, 10))
                continue
                
            resp.raise_for_status()
            data = resp.json()
            
            results = data.get("data", {}).get("results", [])
            total_hits = data.get("data", {}).get("totalDocuments", 0)
            
            if not results:
                print("No results returned. Stopping.")
                break

            # 2. Duplicate Page Detection
            # Hash the IDs on this page to see if we're looping
            current_page_ids = [str(item.get("id")) for item in results]
            page_sig = tuple(current_page_ids)
            if page_sig in seen_page_signatures:
                print(f"Duplicate page signature detected on page {page}. API looping. Stopping.")
                break
            seen_page_signatures.add(page_sig)

            # 3. No New Jobs Check
            new_jobs_on_page = 0
            for item in results:
                job_id = str(item.get("id"))
                
                # If we've seen this job ID before globally, skip adding it? 
                # Or just use it to count "new" items. 
                # We'll just track if we found *any* new item this page.
                if job_id not in seen_ids:
                    seen_ids.add(job_id)
                    new_jobs_on_page += 1
                
                title = item.get("title")
                
                loc_list = []
                if "location" in item and item["location"]:
                    l = item["location"]
                    if isinstance(l, dict):
                        parts = [l.get("city"), l.get("country")]
                        loc_list.append(", ".join([p for p in parts if p]))
                    elif isinstance(l, str):
                        loc_list.append(l)
                
                if "allLocations" in item:
                    for l in item["allLocations"]:
                        if isinstance(l, dict):
                             parts = [l.get("city"), l.get("country")]
                             loc_list.append(", ".join([p for p in parts if p]))

                parsed_locs = [parse_location(l) for l in loc_list]
                
                item_url = item.get("url")
                if item_url and not item_url.startswith("http"):
                    item_url = f"https://www.uber.com{item_url}"
                    
                posted_date = parse_posted_at(item.get("updatedDate") or item.get("creationDate"))
                
                job = {
                    "job_id": job_id,
                    "title": title,
                    "company": "Uber",
                    "locations": parsed_locs,
                    "url": item_url,
                    "employment_type": item.get("type"), 
                    "posted_date": posted_date,
                    "remote_status": None,
                    "description_raw": None, 
                    "department": item.get("department"),
                    "team": None,
                    "sub_teams": None,
                    "source": "uber",
                    "fetched_at": None
                }
                all_jobs.append(job)
            
            # If the page had items but ANY of them were seen before? 
            # Actually, safer: if NO new items were found, stop.
            if new_jobs_on_page == 0:
                print(f"Page {page} returned {len(results)} items but all were seen before. Stopping.")
                break
                
            if len(results) < size:
                break
                
            if total_hits and (page * size >= total_hits):
                break
            
            page += 1
            time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            print(f"Error on Uber page {page}: {e}")
            if 'resp' in locals():
                print(f"Status: {resp.status_code}")
                # print(f"Body: {resp.text[:500]}")
            break
            
    return all_jobs
