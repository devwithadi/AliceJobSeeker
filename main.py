#!/usr/bin/env python3
"""
AliceJobSeeker - Automated job application tool
Main entry point for the application
"""

import os
import json
import time
import datetime
import random
from selenium.webdriver.common.by import By
from threading import Lock
from selenium.common.exceptions import WebDriverException, InvalidSessionIdException, NoSuchWindowException

from selenium_utils import setup_browser, close_browser, handle_privacy_agreement
from job_processor import extract_job_links, process_job, get_more_jobs
from logger import setup_log_directories, log_summary
from resume_parser import get_resume_data

# Global job tracker for preventing reapplications
processed_jobs_lock = Lock()
processed_jobs = set()
recent_job_batches = []  # Track recently seen job batches to detect repetition

def load_configuration(config_file="customization.json"):
    """Load configuration from JSON file"""
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Validate critical configuration fields
        job_search_url = config.get("job_search_url", "").strip()
        if not job_search_url:
            print("ERROR: job_search_url is not configured in customization.json")
            print("Please set a valid job search URL before running.")
            return None
        
        gemini_key = config.get("gemini_api_key", "").strip()
        if not gemini_key:
            print("WARNING: gemini_api_key is not configured in customization.json")
            print("AI features will not work without an API key.")
            print("Get your API key from: https://makersuite.google.com/app/apikey")
        
        # Set defaults for optional fields
        config.setdefault("page_load_wait_time", 5)
        config.setdefault("max_applications", 500)
        config.setdefault("max_jobs_to_process", 500)
        config.setdefault("max_error_count_per_job", 2)
        config.setdefault("log_directory", "logs")
        config.setdefault("max_retries", 3)
        
        return config
    except FileNotFoundError:
        print(f"ERROR: Configuration file not found: {config_file}")
        print("Please create a customization.json file with your settings.")
        print("You can use 'python cli.py --init-config' to create a sample file.")
        return None
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in configuration file: {e}")
        return None
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return None

def load_processed_jobs(file_path="logs/processed_jobs.json"):
    """Load previously processed jobs from JSON file"""
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                job_data = json.load(f)
                return set(job_data.get("processed_jobs", []))
        except Exception as e:
            print(f"Error loading processed jobs: {e}")
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    return set()

def save_processed_jobs(jobs_set, file_path="logs/processed_jobs.json"):
    """Save processed jobs to JSON file"""
    job_data = {"processed_jobs": list(jobs_set)}
    try:
        with open(file_path, 'w') as f:
            json.dump(job_data, f)
    except Exception as e:
        print(f"Error saving processed jobs: {e}")

def is_job_processed(job_url):
    """Check if a job has already been processed"""
    with processed_jobs_lock:
        return job_url in processed_jobs

def mark_job_processed(job_url, success=False):
    """Mark a job as processed in memory"""
    with processed_jobs_lock:
        processed_jobs.add(job_url)
        
        # Save to file every 10 jobs
        if len(processed_jobs) % 10 == 0:
            save_processed_jobs(processed_jobs)

def process_job_batch(driver, job_links, config):
    """Process a batch of jobs sequentially"""
    successful_applications = 0
    failed_applications = 0
    
    # Process only a subset of links per batch to avoid getting stuck in loops
    max_per_batch = min(20, len(job_links))
    job_batch = job_links[:max_per_batch]
    
    for job_url in job_batch:
        if is_job_processed(job_url):
            print(f"Job already processed: {job_url}. Skipping.")
            continue
        
        try:
            print(f"Processing job: {job_url}")
            
            # Navigate to job
            driver.get(job_url)
            time.sleep(3)
            
            # Handle privacy agreements
            attempts = 0
            while attempts < 3 and handle_privacy_agreement(driver):
                time.sleep(2)
                attempts += 1
            
            # Process the job
            success = process_job(driver, job_url, config)
            
            # Record result
            if success:
                successful_applications += 1
                print(f"Successfully applied! Total successful: {successful_applications}")
            else:
                failed_applications += 1
                print(f"Failed to apply. Total failed: {failed_applications}")
            
            # Mark as processed
            mark_job_processed(job_url, success)
            
            # Break if we've reached max applications
            if successful_applications >= config.get("max_applications", 500):
                print(f"Reached target of {successful_applications} successful applications")
                break
                
            # Short pause between jobs
            time.sleep(2)
            
        except Exception as e:
            print(f"Error processing {job_url}: {e}")
            mark_job_processed(job_url, False)
            failed_applications += 1
    
    # Remove processed jobs from the original list to avoid processing them again
    for job_url in job_batch:
        if job_url in job_links:
            job_links.remove(job_url)
    
    return successful_applications, failed_applications

def is_session_valid(driver):
    """Check if the browser session is still valid"""
    try:
        # Try a simple operation that will fail if session is invalid
        driver.title
        return True
    except (InvalidSessionIdException, NoSuchWindowException, WebDriverException):
        return False

def safe_browser_operation(driver, operation_func, *args, **kwargs):
    """Execute a browser operation safely with recovery if needed"""
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            if not is_session_valid(driver):
                print("Browser session is invalid. Creating a new session...")
                # Close the invalid session without throwing errors
                try:
                    driver.quit()
                except:
                    pass
                
                # Create a new browser session
                driver = setup_browser(kwargs.get('config', {}).get('browser_settings', {}))
                
                # If we have a URL to return to, go there
                if 'recovery_url' in kwargs:
                    driver.get(kwargs['recovery_url'])
                    time.sleep(5)  # Wait for page to load
            
            # Perform the requested operation
            return operation_func(driver, *args, **kwargs)
                
        except (InvalidSessionIdException, NoSuchWindowException) as e:
            retry_count += 1
            print(f"Session error: {e}. Retry {retry_count} of {max_retries}")
            
            # If we've exhausted retries, re-throw the exception
            if retry_count >= max_retries:
                raise
                
            # Create a new session for retry
            try:
                driver.quit()
            except:
                pass
            driver = setup_browser(kwargs.get('config', {}).get('browser_settings', {}))
            
        except WebDriverException as e:
            print(f"WebDriver error: {e}")
            retry_count += 1
            
            # If we've exhausted retries, re-throw the exception
            if retry_count >= max_retries:
                raise
            
            time.sleep(2)  # Short pause before retry
    
    return driver  # Return the driver (might be new) if operation fails

def navigate_to_url_safely(driver, url, config):
    """Safely navigate to a URL with error handling"""
    try:
        if not is_session_valid(driver):
            print("Browser session is invalid before navigation. Creating a new session...")
            try:
                driver.quit()
            except:
                pass
            driver = setup_browser(config.get('browser_settings', {}))
            
        print(f"Navigating to: {url}")
        driver.get(url)
        time.sleep(config.get("page_load_wait_time", 5))
        return driver, True
    
    except (InvalidSessionIdException, NoSuchWindowException, WebDriverException) as e:
        print(f"Error navigating to URL: {e}")
        
        # Try to create a new session
        try:
            try:
                driver.quit()
            except:
                pass
            
            print("Creating a new browser session...")
            driver = setup_browser(config.get('browser_settings', {}))
            
            print(f"Retrying navigation to: {url}")
            driver.get(url)
            time.sleep(config.get("page_load_wait_time", 5))
            return driver, True
            
        except Exception as e2:
            print(f"Failed to recover browser session: {e2}")
            return driver, False

def refresh_job_listings(driver, config, page_number=None):
    """Refresh the job listings page to get new recommendations"""
    main_url = config.get("job_search_url")
    
    # Add page number based on Naukri.com pagination pattern
    if page_number and page_number > 1:
        print(f"Constructing URL for page {page_number}...")
        # Parse the base URL
        base_url_parts = main_url.split('?')
        base_url = base_url_parts[0]
        query_params = base_url_parts[1] if len(base_url_parts) > 1 else ""
        
        # Extract job type from URL (e.g., "sales-jobs", "graphic-designer-jobs-in-noida")
        # This handles URLs like "www.naukri.com/sales-jobs" or "www.naukri.com/graphic-designer-jobs-in-noida"
        url_parts = base_url.split('/')
        job_path = url_parts[-1] if url_parts else ""
        
        # Handle different URL patterns
        if "-jobs" in job_path:
            # Case 1: Pattern like /sales-jobs or /graphic-designer-jobs-in-noida
            if job_path.split("-")[-1].isdigit():
                # Already has a page number (e.g., sales-jobs-2)
                job_parts = job_path.split("-")
                job_type_base = "-".join(job_parts[:-1])  # Get everything except the page number
                url_with_page = f"{'/'.join(url_parts[:-1])}/{job_type_base}-{page_number}"
            else:
                # No page number yet (e.g., sales-jobs)
                url_with_page = f"{base_url}-{page_number}"
        else:
            # Case 2: Other URL patterns - just append page number
            url_with_page = f"{base_url}-{page_number}"
        
        # Re-add query parameters
        if query_params:
            url_with_page = f"{url_with_page}?{query_params}"
        
        print(f"Generated pagination URL: {url_with_page}")
        
        # Use safe navigation function
        driver, success = navigate_to_url_safely(driver, url_with_page, config)
        
        if not success:
            print("Failed to navigate to the page. Returning empty job list.")
            return []
    else:
        print(f"Refreshing job listings from page 1: {main_url}")
        
        # Use safe navigation function
        driver, success = navigate_to_url_safely(driver, main_url, config)
        
        if not success:
            print("Failed to navigate to the page. Returning empty job list.")
            return []
    
    time.sleep(config.get("page_load_wait_time", 5))
    
    # Randomize scroll positions to get different results
    try:
        print("Scrolling to load all content...")
        scroll_positions = [0.2, 0.4, 0.6, 0.8, 1.0]
        random.shuffle(scroll_positions)
        
        for scroll_position in scroll_positions:
            try:
                driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {scroll_position});")
                time.sleep(1)
            except WebDriverException as e:
                print(f"Error scrolling: {e}")
                break
    except Exception as e:
        print(f"Error during scroll operations: {e}")
    
    # Try to click "Show More" buttons
    try:
        show_more_buttons = driver.find_elements(By.XPATH, 
            "//button[contains(text(), 'Show More') or contains(text(), 'View More') or contains(text(), 'Load More')]")
        if show_more_buttons:
            for button in show_more_buttons:
                if button.is_displayed():
                    try:
                        driver.execute_script("arguments[0].click();", button)
                        print("Clicked 'Show More' button")
                        time.sleep(3)
                    except:
                        pass
    except Exception as e:
        print(f"Error clicking Show More button: {e}")
    
    # Extract job links with exception handling
    job_links = []
    try:
        job_links = extract_job_links(driver, config)
    except (InvalidSessionIdException, NoSuchWindowException, WebDriverException) as e:
        print(f"Error extracting job links: {e}")
        # Attempt to recreate the session if needed
        try:
            driver = setup_browser(config.get("browser_settings", {}))
            driver.get(main_url)
            time.sleep(config.get("page_load_wait_time", 5))
            job_links = extract_job_links(driver, config)
        except Exception as e2:
            print(f"Failed to recover and extract job links: {e2}")
    
    # Keep track of seen job URLs to detect loops
    if job_links:
        global recent_job_batches
        try:
            # Create a fingerprint of the first few links (use try block in case job_links is empty)
            fingerprint_links = job_links[:10] if len(job_links) >= 10 else job_links
            job_urls_fingerprint = hash(tuple(sorted(fingerprint_links)))
            recent_job_batches.append(job_urls_fingerprint)
            
            # Keep only the last 5 batches
            if len(recent_job_batches) > 5:
                recent_job_batches.pop(0)
        except Exception as e:
            print(f"Error tracking job batches: {e}")
    
    return job_links

def is_search_stuck(min_repeats=3):
    """Check if we're stuck in a loop of seeing the same jobs"""
    global recent_job_batches
    if len(recent_job_batches) < min_repeats:
        return False
        
    # If we've seen the same batch of links multiple times, we're stuck
    last_batch = recent_job_batches[-1]
    repeat_count = recent_job_batches.count(last_batch)
    
    return repeat_count >= min_repeats

def main():
    """Main entry point for AliceJobSeeker application"""
    global processed_jobs
    
    # Load configuration
    config = load_configuration()
    
    # Exit if configuration is invalid
    if config is None:
        print("\nFailed to load configuration. Exiting.")
        return
    
    # Load resume data from PDF if configured with error handling
    try:
        resume_data = get_resume_data(config)
        if resume_data and isinstance(resume_data, dict) and resume_data.get("name"):
            print(f"Loaded resume data for {resume_data.get('name')}")
        else:
            print("WARNING: Resume data was not loaded successfully or is incomplete")
            # Create fallback resume data
            resume_data = {
                "name": "Job Applicant",
                "email": config.get("default_answers", {}).get("email", "applicant@example.com"),
                "phone": "Not specified",
                "experience": config.get("default_answers", {}).get("experience", "3 years"),
                "skills": ["Not specified"],
                "education": ["Not specified"]
            }
            print("Created fallback resume data to continue operation")
            
        # Debug output to check what was actually loaded
        print(f"Resume data keys: {list(resume_data.keys()) if isinstance(resume_data, dict) else 'Not a dictionary'}")
        
    except Exception as e:
        print(f"ERROR: Failed to load resume data: {e}")
        # Create fallback resume data
        resume_data = {
            "name": "Job Applicant",
            "email": config.get("default_answers", {}).get("email", "applicant@example.com"),
            "phone": "Not specified",
            "experience": "Not specified",
            "skills": ["Not specified"],
            "education": ["Not specified"]
        }
        print("Created fallback resume data to continue operation")
    
    # Setup logging directories
    setup_log_directories(config.get("log_directory", "logs"))
    
    # Load previously processed jobs
    processed_jobs = load_processed_jobs()
    print(f"Loaded {len(processed_jobs)} previously processed jobs")
    
    # Set up browser for job discovery
    driver = None
    try:
        driver = setup_browser(config.get("browser_settings", {}))
    except Exception as e:
        print(f"Failed to set up browser: {e}")
        return
    
    # Use job search URL from config
    main_url = config.get("job_search_url")
    print(f"Navigating to job search URL: {main_url}")
    
    try:
        driver.get(main_url)
        # Wait for page to load
        time.sleep(config.get("page_load_wait_time", 5))
    except Exception as e:
        print(f"Error navigating to main URL: {e}")
        if driver:
            close_browser(driver)
        return
    
    # Extract initial job links
    job_links = []
    try:
        job_links = extract_job_links(driver, config)
        print(f"Initially found {len(job_links)} job links")
    except Exception as e:
        print(f"Error extracting initial job links: {e}")
        
        # Try to recover
        try:
            print("Attempting to recover browser session...")
            close_browser(driver)
            driver = setup_browser(config.get("browser_settings", {}))
            driver.get(main_url)
            time.sleep(config.get("page_load_wait_time", 5))
            job_links = extract_job_links(driver, config)
            print(f"Recovered session and found {len(job_links)} job links")
        except Exception as e2:
            print(f"Failed to recover session: {e2}")
            if driver:
                close_browser(driver)
            return
    
    # Filter out already processed jobs
    unprocessed_jobs = [url for url in job_links if not is_job_processed(url)]
    print(f"Found {len(unprocessed_jobs)} unprocessed jobs")
    
    successful_applications = 0
    failed_applications = 0
    refresh_count = 0
    max_applications = config.get("max_applications", 500)
    max_refresh_attempts = config.get("max_retries", 3) * 5  # Increase max refresh attempts
    current_page = 1
    stuck_count = 0
    max_page_to_try = 20  # Don't go beyond 20 pages
    browser_reset_count = 0
    
    while successful_applications < max_applications:
        # Check if browser session is still valid
        if not is_session_valid(driver) or browser_reset_count >= 5:
            print("Browser session is invalid or needs reset. Creating a new session...")
            try:
                close_browser(driver)
            except:
                pass
                
            try:
                driver = setup_browser(config.get("browser_settings", {}))
                browser_reset_count = 0  # Reset counter after successful browser creation
            except Exception as e:
                print(f"Failed to create new browser session: {e}")
                time.sleep(30)  # Wait longer before next attempt
                continue
        
        # Process batch of unprocessed jobs
        if unprocessed_jobs:
            try:
                batch_success, batch_failed = process_job_batch(driver, unprocessed_jobs, config)
                successful_applications += batch_success
                failed_applications += batch_failed
                
                # If we processed jobs successfully, reset browser reset counter
                if batch_success > 0 or batch_failed > 0:
                    browser_reset_count = 0
            except (InvalidSessionIdException, NoSuchWindowException, WebDriverException) as e:
                print(f"Browser session error during batch processing: {e}")
                browser_reset_count += 1
                continue  # Skip to next iteration to reset browser
        
        # If we've reached our target, break
        if successful_applications >= max_applications:
            print(f"Reached target of {max_applications} successful applications")
            break
        
        # If we're running low on jobs or empty, try next page
        if len(unprocessed_jobs) == 0:
            # Try to move to next page
            current_page += 1
            if current_page > max_page_to_try:
                print(f"Reached maximum page number ({max_page_to_try}). Stopping search.")
                break
                
            print(f"No more jobs on current page. Moving to page {current_page}...")
            
            try:
                # Force the pagination to go to the next page
                print(f"Navigating to page {current_page} for more jobs...")
                new_job_links = refresh_job_listings(driver, config, current_page)
                
                # If the refresh_job_listings recreated the driver, capture it
                if isinstance(new_job_links, tuple) and len(new_job_links) == 2:
                    driver, new_job_links = new_job_links  # Unpack
                
                # Filter out processed jobs
                new_unprocessed_jobs = [url for url in new_job_links if not is_job_processed(url)]
                print(f"Found {len(new_unprocessed_jobs)} new unprocessed jobs on page {current_page}")
                
                # Add additional debugging info
                print(f"Total job links on page {current_page}: {len(new_job_links)}")
                
                # If no new jobs found, try another page rather than quitting
                if not new_unprocessed_jobs and current_page < max_page_to_try:
                    print(f"No new jobs on page {current_page}, trying page {current_page+1}...")
                    continue
                
                # Only try modifying search if we've tried multiple pages with no success
                if not new_unprocessed_jobs and current_page > 4:
                    # Try a completely different approach - change search parameters slightly
                    original_url = config.get("job_search_url")
                    if "experience=" in original_url:
                        # Modify experience parameter to get different results
                        modified_url = original_url.replace("experience=3", f"experience={random.choice([2,4,5])}")
                        print(f"Trying modified search URL: {modified_url}")
                        driver.get(modified_url)
                        time.sleep(config.get("page_load_wait_time", 5))
                        
                        # Extract from modified search
                        new_job_links = extract_job_links(driver, config)
                        new_unprocessed_jobs = [url for url in new_job_links if not is_job_processed(url)]
                        print(f"Found {len(new_unprocessed_jobs)} new unprocessed jobs with modified search")
                        
                        # If still no new jobs, we should exit
                        if not new_unprocessed_jobs:
                            print("No more unprocessed jobs available even with modified search. Exiting.")
                            break
            
            except (InvalidSessionIdException, NoSuchWindowException, WebDriverException) as e:
                print(f"Session error while refreshing job listings: {e}")
                browser_reset_count += 1
                continue  # Skip to next iteration to reset browser
            
            # Update unprocessed jobs list
            unprocessed_jobs = new_unprocessed_jobs
        
        # Periodic refresh (every 3 batches) to find more opportunities even if we still have jobs
        elif refresh_count % 3 == 0:
            print("Periodically refreshing job listings to find more opportunities...")
            refresh_count += 1
            
            # Get more jobs using current page + 1 for variety
            new_page = current_page + 1
            if new_page <= max_page_to_try:
                new_job_links = refresh_job_listings(driver, config, new_page)
                
                # Filter out processed jobs
                new_unprocessed_jobs = [url for url in new_job_links if not is_job_processed(url)]
                print(f"Found {len(new_unprocessed_jobs)} new unprocessed jobs on page {new_page}")
                
                # Add to existing unprocessed jobs
                if new_unprocessed_jobs:
                    current_page = new_page  # Update current page only if we found new jobs
                    unprocessed_jobs.extend(new_unprocessed_jobs)
                    
                    # Deduplicate
                    unprocessed_jobs = list(set(unprocessed_jobs))
        
        # Increment refresh counter
        refresh_count += 1
        
        # Check if we're stuck in a loop
        if is_search_stuck(3):
            stuck_count += 1
            print(f"Warning: Search appears to be stuck in a loop. Attempt {stuck_count}/3 to break out")
            
            if stuck_count >= 3:
                print("Breaking out of search loop - not finding new jobs")
                
                # Try a completely different approach - change search parameters slightly
                original_url = config.get("job_search_url")
                if "experience=" in original_url:
                    # Modify experience parameter to get different results
                    modified_url = original_url.replace("experience=3", f"experience={random.choice([2,4,5])}")
                    print(f"Trying modified search URL: {modified_url}")
                    driver.get(modified_url)
                    time.sleep(config.get("page_load_wait_time", 5))
                    
                    # Extract from modified search
                    new_job_links = extract_job_links(driver, config)
                    new_unprocessed_jobs = [url for url in new_job_links if not is_job_processed(url)]
                    print(f"Found {len(new_unprocessed_jobs)} new unprocessed jobs with modified search")
                    
                    # Reset stuck counter
                    stuck_count = 0
                    
                    # If still no new jobs, we should exit
                    if not new_unprocessed_jobs:
                        print("No more unprocessed jobs available even with modified search. Exiting.")
                        break
        
        # Break if we've tried too many times without finding new jobs
        if not unprocessed_jobs and refresh_count >= max_refresh_attempts:
            print(f"Attempted to refresh {max_refresh_attempts} times with no new jobs. Exiting.")
            break
    
    # Save final processed jobs list
    save_processed_jobs(processed_jobs)
    
    # Log summary
    log_summary(successful_applications, failed_applications, config)
    
    # Close browser
    try:
        close_browser(driver)
    except:
        pass

if __name__ == "__main__":
    main()
