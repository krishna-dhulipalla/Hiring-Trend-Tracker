
import json
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.fetchers.custom import google

def run():
    print("Running Google Fetcher Test...")
    url = "https://www.google.com/about/careers/applications/jobs/results?location=United%20States"
    # Pass max_pages parameter
    jobs = google.fetch_jobs(url, max_pages=2)
    
    print(json.dumps(jobs, indent=2, default=str))
    print(f"Summary: {{ adapter: 'google', items: {len(jobs)} }}")

if __name__ == "__main__":
    run()
