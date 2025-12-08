import os
import json
import sys

# Ensure src module is in path
sys.path.append(os.getcwd())

from src.analytics.daily_sync import sync_job_diff

DATA_DIFFS_DIR = "data/diffs"

def backfill_diffs():
    print("Starting backfill of job diffs to DB...")
    
    if not os.path.exists(DATA_DIFFS_DIR):
        print(f"Directory {DATA_DIFFS_DIR} does not exist.")
        return

    count = 0
    errors = 0
    
    # Iterate over ATS folders
    for ats in os.listdir(DATA_DIFFS_DIR):
        ats_dir = os.path.join(DATA_DIFFS_DIR, ats)
        if not os.path.isdir(ats_dir):
            continue
            
        # Iterate over Company folders
        for company_slug in os.listdir(ats_dir):
            slug_dir = os.path.join(ats_dir, company_slug)
            if not os.path.isdir(slug_dir):
                continue
                
            # Iterate over diff files
            for filename in os.listdir(slug_dir):
                if not filename.endswith(".json"):
                    continue
                
                filepath = os.path.join(slug_dir, filename)
                
                # Extract timestamp from filename
                # Format: jobs_diff_{slug}_{timestamp}.json OR just {timestamp}.json
                # We need the timestamp part.
                try:
                    parts = filename.replace(".json", "").split("_")
                    run_timestamp = parts[-1]
                    
                    # Basic validation of timestamp format (optional but good)
                    # 2025-12-08T00-41-14Z is length 20
                    if len(run_timestamp) < 15: 
                         print(f"Skipping {filename}, could not parse timestamp.")
                         continue

                    with open(filepath, 'r', encoding='utf-8') as f:
                        diff_data = json.load(f)
                    
                    # Call the existing sync function
                    # It handles parsing the timestamp to date
                    sync_job_diff(diff_data, company_slug, run_timestamp)
                    print(f"Synced {company_slug} - {run_timestamp}")
                    count += 1
                    
                except Exception as e:
                    print(f"Failed to process {filename}: {e}")
                    errors += 1

    print(f"Backfill complete. Synced {count} files. Errors: {errors}")

if __name__ == "__main__":
    backfill_diffs()
