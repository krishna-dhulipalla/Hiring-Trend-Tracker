import os
import json
import logging
import datetime
from src.fetchers import greenhouse, lever, ashby, smartrecruiters, workday

from src.utils import is_valid_job, is_us_eligible
from src import diff

def setup_logging(run_timestamp):
    """Sets up logging for the current run."""
    log_dir = os.path.join("logs", run_timestamp)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    success_log = os.path.join(log_dir, "success.log")
    failure_log = os.path.join(log_dir, "failure.log")
    
    # Create distinct loggers
    success_logger = logging.getLogger('success')
    success_logger.setLevel(logging.INFO)
    success_handler = logging.FileHandler(success_log, mode='w', encoding='utf-8')
    success_handler.setFormatter(logging.Formatter('%(message)s'))
    success_logger.addHandler(success_handler)
    
    failure_logger = logging.getLogger('failure')
    failure_logger.setLevel(logging.ERROR)
    failure_handler = logging.FileHandler(failure_log, mode='w', encoding='utf-8')
    failure_handler.setFormatter(logging.Formatter('%(message)s'))
    failure_logger.addHandler(failure_handler)
    
    # Console logger for general progress
    console_logger = logging.getLogger('console')
    console_logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(message)s'))
    console_logger.addHandler(console_handler)

    return success_logger, failure_logger, console_logger

def get_fetcher(ats_name):
    """Returns the fetcher module based on ATS name."""
    if ats_name == "greenhouse":
        return greenhouse
    elif ats_name == "lever":
        return lever
    elif ats_name == "ashby":
        return ashby
    elif ats_name == "smartrecruiters":
        return smartrecruiters
    elif ats_name == "workday":
        return workday
    else:
        raise ValueError(f"Unknown ATS: {ats_name}")

def save_json(data, filepath):
    """Saves data to a JSON file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_companies():
    """Loads companies from src/companies.json."""
    companies_path = os.path.join(os.path.dirname(__file__), "companies.json")
    with open(companies_path, 'r') as f:
        return json.load(f)

def main():
    # 1. Compute run timestamp
    # Format: 2025-12-04T19-00-00Z
    run_timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
    
    # 2. Setup logging
    success_logger, failure_logger, console_logger = setup_logging(run_timestamp)
    console_logger.info(f"Starting run at {run_timestamp}")

    # 3. Load companies
    try:
        companies = load_companies()
    except Exception as e:
        console_logger.error(f"Failed to load companies.json: {e}")
        return

    # 4. Loop over companies
    for company in companies:
        slug = company["slug"]
        ats = company["ats"]
        
        try:
            fetcher = get_fetcher(ats)
            
            # Fetch data
            raw_jobs = fetcher.fetch_jobs(slug)

            # Normalize data (needed for filtering)
            if hasattr(fetcher, 'normalize_job'):
                normalized_jobs = [fetcher.normalize_job(job) for job in raw_jobs]
            else:
                normalized_jobs = raw_jobs

            # Inject company_slug
            for job in normalized_jobs:
                job["company_slug"] = slug

            # Filter jobs
            filtered_jobs = [
                job for job in normalized_jobs 
                if is_valid_job(job.get('title')) and is_us_eligible(job)
            ]

            # Write files
            # Raw data
            raw_path = f"data/raw/{ats}/{slug}/{run_timestamp}.json"
            save_json(raw_jobs, raw_path)
            
            # Filtered data
            filtered_path = f"data/filtered/{ats}/{slug}/{run_timestamp}.json"
            save_json(filtered_jobs, filtered_path)
            
            # Log success
            msg = f"{slug} - {ats} - {len(raw_jobs)} raw, {len(filtered_jobs)} filtered"
            success_logger.info(msg)
            console_logger.info(f"OK {msg}")

            # Generate Diff (History Brain)
            try:
                # Filtered snapshots are stored in filtered_path's directory
                snapshot_dir = os.path.dirname(filtered_path)
                
                # We want diffs to live in data/diffs/{ats}/{slug}/
                diff_dir = f"data/diffs/{ats}/{slug}"
                
                diff.generate_diff(
                    company_slug=slug,
                    current_ts=run_timestamp,
                    current_snapshot_data=filtered_jobs,
                    snapshot_dir=snapshot_dir,
                    diff_dir=diff_dir
                )
                
                # Sync to Analytics DB
                try:
                    from src.analytics.daily_sync import sync_job_diff
                    # Fix: use the correct filename pattern
                    diff_file = os.path.join(diff_dir, f"jobs_diff_{slug}_{run_timestamp}.json")
                    if os.path.exists(diff_file):
                        with open(diff_file, 'r', encoding='utf-8') as f:
                            diff_data = json.load(f)
                        sync_job_diff(diff_data, slug, run_timestamp)
                except Exception as e:
                    console_logger.error(f"Analytics sync failed for {slug}: {e}")
            except Exception as e:
                err_msg = f"Diff generation failed for {slug}: {e}"
                console_logger.error(err_msg)
                failure_logger.error(err_msg)


        except Exception as e:
            # Write error marker with full stack trace
            error_path = f"data/raw/{ats}/{slug}/{run_timestamp}_ERROR.txt"
            os.makedirs(os.path.dirname(error_path), exist_ok=True)
            with open(error_path, 'w', encoding='utf-8') as f:
                f.write(str(e))
            
            # Log failure
            msg = f"{slug} - {ats} -> {error_path}"
            failure_logger.error(msg)
            console_logger.error(f"ERROR {msg}")

if __name__ == "__main__":
    main()
