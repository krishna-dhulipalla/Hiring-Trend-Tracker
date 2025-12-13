
import os
import json
import logging
from src.jobs.fetchers import greenhouse, lever, ashby, smartrecruiters, workday
from src.jobs.fetchers.custom import google, meta, amazon, uber, apple
from src.utils import is_valid_job, is_us_eligible
from src.jobs import diff

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
    elif ats_name == "google":
        return google
    elif ats_name == "meta":
        return meta
    elif ats_name == "amazon":
        return amazon
    elif ats_name == "uber":
        return uber
    elif ats_name == "apple":
        return apple
    else:
        raise ValueError(f"Unknown ATS: {ats_name}")

def save_json(data, filepath):
    """Saves data to a JSON file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def run(run_timestamp, companies):
    logger = logging.getLogger("jobs")
    logger.info("--- Starting Job Pipeline ---")
    
    total_raw = 0
    total_filtered = 0
    stats = []

    for company in companies:
        slug = company["slug"]
        ats = company["ats"]
        
        try:
            fetcher = get_fetcher(ats)
            logger.info(f"Fetching {slug} ({ats})...")
            
            # Fetch data
            if ats in ["google", "meta", "amazon", "uber", "apple"]:
                config = company.get("config", {})
                raw_jobs = fetcher.fetch_jobs(config)
            else:
                raw_jobs = fetcher.fetch_jobs(slug)

            # Normalize data
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
            raw_path = f"data/raw/{ats}/{slug}/{run_timestamp}.json"
            save_json(raw_jobs, raw_path)
            
            filtered_path = f"data/filtered/{ats}/{slug}/{run_timestamp}.json"
            save_json(filtered_jobs, filtered_path)
            
            msg = f"{slug}: {len(raw_jobs)} raw, {len(filtered_jobs)} filtered"
            logger.info(msg)
            stats.append(msg)
            
            total_raw += len(raw_jobs)
            total_filtered += len(filtered_jobs)

            # Generate Diff
            try:
                snapshot_dir = os.path.dirname(filtered_path)
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
                    diff_file = os.path.join(diff_dir, f"jobs_diff_{slug}_{run_timestamp}.json")
                    if os.path.exists(diff_file):
                        with open(diff_file, 'r', encoding='utf-8') as f:
                            diff_data = json.load(f)
                        sync_job_diff(diff_data, slug, run_timestamp)
                except ImportError:
                    logger.warning("Analytics module not found, skipping sync.")
                except Exception as e:
                    logger.error(f"Analytics sync failed for {slug}: {e}")

            except Exception as e:
                logger.error(f"Diff generation failed for {slug}: {e}")

        except Exception as e:
            error_path = f"data/raw/{ats}/{slug}/{run_timestamp}_ERROR.txt"
            os.makedirs(os.path.dirname(error_path), exist_ok=True)
            with open(error_path, 'w', encoding='utf-8') as f:
                f.write(str(e))
            logger.error(f"Failed {slug}: {e}")
            stats.append(f"{slug}: FAILED")

    logger.info("--- Job Pipeline Complete ---")
    return {
        "raw": total_raw,
        "filtered": total_filtered,
        "details": stats
    }
