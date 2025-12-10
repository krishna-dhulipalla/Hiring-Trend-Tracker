
import json
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.fetchers.custom import meta

def run():
    print("Running Meta Fetcher Test...")
    config = {
        "doc_id": "CareersJobSearchResultsV3DataQuery",
        "variables": {
            "search_input": {
                "q": "software",
                "divisions": [],
                "offices": [],
                "results_per_page": 10
            }
        }
    }
    
    jobs = meta.fetch_jobs(config, max_pages=2)
    
    print(json.dumps(jobs, indent=2, default=str))
    print(f"Summary: {{ adapter: 'meta', items: {len(jobs)} }}")

if __name__ == "__main__":
    run()
