
import requests
import time
import random
import re
from bs4 import BeautifulSoup
from src.utils import parse_location

def fetch_jobs(config, max_pages=None):
    """
    Fetches jobs from Google Careers.
    config: URL string OR dict with 'url' key.
    max_pages: Optional int limit for testing.
    """
    if isinstance(config, dict):
        url = config.get("url")
    else:
        url = config

    if not url:
        raise ValueError("Google fetcher requires 'url' in config.")
    all_jobs = []
    page = 1
    
    if '?' not in url:
        url += '?'
    
    base_url = url
    
    SAFE_MAX_PAGES = 2000
    seen_ids = set()
    seen_page_signatures = set()
    
    while True:
        if max_pages and page > max_pages:
            print(f"Reached max_pages {max_pages}. Stopping.")
            break
        if page >= SAFE_MAX_PAGES:
            print(f"Reached safe limit {SAFE_MAX_PAGES}. Stopping.")
            break
            
        target_url = f"{base_url}&page={page}"
        print(f"Fetching Google page {page}...")
        
        try:
            resp = requests.get(target_url)
            if resp.status_code in [429, 500, 502, 503, 504]:
                print(f"Got {resp.status_code}, backing off...")
                time.sleep(random.uniform(5, 10))
                continue
            
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            cards = soup.select('ul.spHGqe > li.lLd3Je')
            
            if not cards:
                print(f"No cards found on page {page}. Stopping.")
                break
                
            print(f"Found {len(cards)} cards on page {page}.")
            
            page_jobs = []
            page_ids = []
            new_jobs_on_page = 0
            
            for card in cards:
                title_elem = card.select_one('h3.QJPWVe')
                title = title_elem.get_text(strip=True) if title_elem else None
                company = "Google"
                
                loc_elems = card.select('.r0wTof')
                raw_locs = [el.get_text(strip=True) for el in loc_elems]
                locations = [parse_location(l) for l in raw_locs]
                
                link_elem = card.select_one('a[href^="jobs/results/"]')
                item_url = None
                job_id = None
                
                if link_elem:
                    href = link_elem.get('href')
                    item_url = f"https://www.google.com/about/careers/applications/{href}"
                    match = re.search(r'jobs/results/(\d+)', href)
                    if match:
                        job_id = match.group(1)
                
                if not job_id:
                    if item_url:
                        job_id = str(abs(hash(item_url)))
                    else:
                        job_id = str(abs(hash(title + str(raw_locs))))
                
                page_ids.append(job_id)
                
                if job_id not in seen_ids:
                    seen_ids.add(job_id)
                    new_jobs_on_page += 1

                job = {
                    "job_id": job_id,
                    "title": title,
                    "company": company,
                    "locations": locations,
                    "url": item_url,
                    "employment_type": None,
                    "posted_date": None, 
                    "remote_status": None,
                    "description_raw": None, 
                    "department": None,
                    "team": None,
                    "sub_teams": None,
                    "source": "google",
                    "fetched_at": None 
                }
                
                page_jobs.append(job)
            
            if not page_jobs:
                print("No jobs extracted from cards. Stopping.")
                break

            # Duplicate Page Check
            page_sig = tuple(page_ids)
            if page_sig in seen_page_signatures:
                print(f"Duplicate page signature on page {page}. Stopping.")
                break
            seen_page_signatures.add(page_sig)
            
            if new_jobs_on_page == 0:
                print(f"Page {page} returned {len(page_jobs)} items but all were seen before. Stopping.")
                break

            all_jobs.extend(page_jobs)
            
            if len(cards) < 20:
                print(f"Page {page} has {len(cards)} items (< 20). Stopping.")
                break
                
            page += 1
            time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            print(f"Error on page {page}: {e}")
            break
            
    return all_jobs
