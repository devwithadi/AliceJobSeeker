"""
AliceJobSeeker - Job Processing Module
Handles job extraction, matching, and application
"""

import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from selenium_utils import is_html_response
from logger import (save_job_log, save_question_log, save_preference_match_log)
from gemini_api import bard_flash_response

def extract_job_links(driver, config, page=1, existing_links=None):
    """Extract job links from the search results page with focus on recommended jobs"""
    print(f"Extracting job links from page {page}...")
    
    if existing_links is None:
        job_links = []
    else:
        job_links = existing_links.copy()
        
    initial_count = len(job_links)
    
    # Check for loading screen/splashscreen
    splash_screens = driver.find_elements(By.CLASS_NAME, "styles_splashscreen-container__jxBax")
    if splash_screens:
        print("Detected splash screen. Waiting for content to load...")
        # Wait longer for the actual content to load
        wait_time = config.get("page_load_wait_time", 5) * 3
        for i in range(wait_time):
            print(f"Waiting {wait_time - i} more seconds for content...")
            time.sleep(1)
            
            # Try to refresh if needed
            if i > wait_time / 2 and len(driver.find_elements(By.CLASS_NAME, "styles_splashscreen-container__jxBax")) > 0:
                print("Still on splash screen. Refreshing...")
                driver.refresh()
    
    # Wait for job cards with more robust waiting
    wait = WebDriverWait(driver, config.get("selenium_timeouts", {}).get("page_load", 15))
    
    # First, try the div[data-job-id] selector which is known to work well
    try:
        print("Extracting job links using div[data-job-id] selector")
        job_cards = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div[data-job-id]")))
        
        if job_cards:
            print(f"Found {len(job_cards)} job cards with div[data-job-id] selector")
            
            for card in job_cards:
                try:
                    # Find the link element in the job card
                    link_elements = card.find_elements(By.TAG_NAME, "a")
                    for link in link_elements:
                        job_url = link.get_attribute("href")
                        if job_url and "/job-listings" in job_url and job_url not in job_links:
                            job_links.append(job_url)
                            print(f"Added job URL: {job_url}")
                except Exception as e:
                    print(f"Error processing job card: {e}")
    except TimeoutException:
        print("Timeout waiting for job cards with div[data-job-id] selector")
    except Exception as e:
        print(f"Error with div[data-job-id] selector: {e}")
    
    # If we didn't find any links with the preferred selector, try the other selectors as fallback
    if len(job_links) == initial_count:
        print("No job links found with div[data-job-id] selector. Trying alternative selectors...")
        
        # Try other selectors in a specific order
        selectors = [
            "article.jobTuple", 
            ".jobTitle",
            ".title",
            "a[href*='/job-listings']"
        ]
        
        # Try each selector
        for selector in selectors:
            try:
                print(f"Trying to find job cards with selector: {selector}")
                elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector)))
                if elements:
                    print(f"Found {len(elements)} elements with selector: {selector}")
                    
                    # If we found job titles/links directly
                    if selector == ".jobTitle" or selector == ".title" or selector == "a[href*='/job-listings']":
                        for element in elements:
                            try:
                                if selector.startswith("a"):
                                    job_url = element.get_attribute("href")
                                    if job_url and "/job-listings" in job_url and job_url not in job_links:
                                        job_links.append(job_url)
                                        print(f"Added job URL: {job_url}")
                                else:
                                    # For titles, find the parent link
                                    parent_elements = element.find_elements(By.XPATH, "./ancestor::a")
                                    if parent_elements:
                                        job_url = parent_elements[0].get_attribute("href")
                                        if job_url and job_url not in job_links:
                                            job_links.append(job_url)
                                            print(f"Added job URL from title: {job_url}")
                            except Exception as e:
                                print(f"Error processing element: {e}")
                    # For job cards, find the links inside
                    else:
                        for card in elements:
                            try:
                                link_elements = card.find_elements(By.TAG_NAME, "a")
                                for link in link_elements:
                                    job_url = link.get_attribute("href")
                                    if job_url and "/job-listings" in job_url and job_url not in job_links:
                                        job_links.append(job_url)
                                        print(f"Added job URL from card: {job_url}")
                            except Exception as e:
                                print(f"Error processing job card: {e}")
                    
                    # If we found at least some links, break out of the selector loop
                    if len(job_links) > initial_count:
                        break
            except TimeoutException:
                print(f"Timeout waiting for elements with selector: {selector}")
            except Exception as e:
                print(f"Error with selector {selector}: {e}")
    
    # If no job cards found with any selector, try a more aggressive approach
    if len(job_links) == initial_count:
        print("No job links found with standard selectors. Trying direct approach...")
        try:
            # Get all links on the page
            all_links = driver.find_elements(By.TAG_NAME, "a")
            print(f"Found {len(all_links)} total links on page")
            
            # Filter for job listing links
            for link in all_links:
                try:
                    job_url = link.get_attribute("href")
                    if job_url and "/job-listings" in job_url and job_url not in job_links:
                        job_links.append(job_url)
                        print(f"Found job via direct link approach: {job_url}")
                except Exception as e:
                    continue
                    
            # If still no links found, check if we need to log in first
            if len(job_links) == initial_count:
                login_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Login')]")
                if login_elements:
                    print("Login button detected - you may need to login first")
                    
        except Exception as e:
            print(f"Error with direct link extraction: {e}")
    
    new_links = len(job_links) - initial_count
    print(f"Extracted {new_links} new job links from page {page}")
    print(f"Total job links found: {len(job_links)}")
    
    # If we still couldn't find any job links, try saving a screenshot for debugging
    if len(job_links) == initial_count:
        print("WARNING: Unable to extract any job links from the page!")
        try:
            screenshot_path = f"logs/page_screenshot_page{page}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
            driver.save_screenshot(screenshot_path)
            print(f"Saved screenshot to {screenshot_path} for debugging")
        except Exception as e:
            print(f"Failed to save screenshot: {e}")
            
        # Suggest checking login status
        print("Suggestions for troubleshooting:")
        print("1. Check if you need to log in first")
        print("2. Verify if the search URL in customization.json is correct")
        print("3. The website structure may have changed, requiring code updates")
    
    return job_links

def get_more_jobs(driver, config, current_jobs=None, max_pages=10):
    """Navigate to next pages to get more jobs"""
    if current_jobs is None:
        job_links = []
    else:
        job_links = current_jobs.copy()
    
    current_page = 1
    max_jobs = config.get("max_jobs_to_process", 500)
    
    # For recommended jobs page, scroll and look for "show more" buttons
    if "/mnjuser/recommendedjobs" in driver.current_url:
        while current_page < max_pages:
            # Scroll down to trigger lazy loading
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            print("Scrolled to bottom to trigger lazy loading")
            time.sleep(3)
            
            # Look for "Show More" buttons
            try:
                for text in ["Show More", "View More", "Load More", "See More"]:
                    buttons = driver.find_elements(By.XPATH, f"//button[contains(text(), '{text}')]")
                    if not buttons:
                        buttons = driver.find_elements(By.XPATH, f"//a[contains(text(), '{text}')]")
                    
                    if buttons:
                        for button in buttons:
                            if button.is_displayed():
                                driver.execute_script("arguments[0].click();", button)
                                print(f"Clicked '{text}' button")
                                time.sleep(3)
                                break
            except Exception as e:
                print(f"Error clicking load more button: {e}")
            
            # Extract new job links
            new_links_count = len(job_links)
            job_links = extract_job_links(driver, config, current_page + 1, job_links)
            
            # If no new links found after scrolling, we've reached the end
            if len(job_links) == new_links_count:
                print("No new links found after scrolling/loading more. Stopping extraction.")
                break
                
            current_page += 1
    else:
        # Standard pagination for regular search pages
        while len(job_links) < max_jobs and current_page < max_pages:
            success = navigate_to_next_page(driver, current_page)
            if not success:
                print("Failed to navigate to next page. Stopping extraction.")
                break
                
            current_page += 1
            
            # Extract job links from current page
            job_links = extract_job_links(driver, config, current_page, job_links)
            
            # Add a short delay to avoid rate limiting
            time.sleep(2)
    
    return job_links

def navigate_to_next_page(driver, current_page):
    """Navigate to the next page of job search results"""
    print(f"Navigating to page {current_page + 1}...")
    
    # Check if we're on the recommended jobs page, which has a different pagination system
    if "/mnjuser/recommendedjobs" in driver.current_url:
        try:
            # Try scrolling first to trigger lazy loading
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            print("Scrolled to bottom to trigger lazy loading")
            time.sleep(3)
            
            # Look for "Show More" buttons with multiple text variations
            load_more_button_found = False
            for text in ["Show More", "View More", "Load More", "See More", "More Jobs"]:
                buttons = driver.find_elements(By.XPATH, f"//button[contains(text(), '{text}')]")
                if not buttons:
                    buttons = driver.find_elements(By.XPATH, f"//a[contains(text(), '{text}')]")
                
                if buttons:
                    for button in buttons:
                        if button.is_displayed():
                            try:
                                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", button)
                                time.sleep(1)
                                driver.execute_script("arguments[0].click();", button)
                                print(f"Clicked '{text}' button")
                                load_more_button_found = True
                                time.sleep(3)  # Wait for new jobs to load
                                break
                            except Exception as e:
                                print(f"Error clicking {text} button: {e}")
                    
                    if load_more_button_found:
                        break
            
            # Try finding and clicking pagination elements
            if not load_more_button_found:
                pagination_elements = driver.find_elements(By.CSS_SELECTOR, ".pagination, .page-link, .page-item")
                for element in pagination_elements:
                    if element.is_displayed():
                        try:
                            driver.execute_script("arguments[0].click();", element)
                            print("Clicked pagination element")
                            time.sleep(3)
                            return True
                        except:
                            pass
            
            # If we found and clicked a load more button, return success
            return load_more_button_found
            
        except Exception as e:
            print(f"Error navigating recommended jobs page: {e}")
            return False
    
    try:
        # Look for pagination controls
        pagination_found = False
        
        # Strategy 1: Look for next button
        next_buttons = driver.find_elements(By.XPATH, 
            "//a[contains(@class, 'fright') or contains(@class, 'nextPage') or contains(text(), 'Next')]")
        
        if next_buttons:
            for next_button in next_buttons:
                if next_button.is_displayed():
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_button)
                        time.sleep(1)
                        driver.execute_script("arguments[0].click();", next_button)
                        print(f"Clicked on Next button to navigate to page {current_page + 1}")
                        pagination_found = True
                        time.sleep(3)  # Wait for the page to load
                        break
                    except Exception as e:
                        print(f"Error clicking Next button: {e}")
        
        # Strategy 2: Look for page number links
        if not pagination_found:
            page_links = driver.find_elements(By.CSS_SELECTOR, "a.page-link, a.page")
            next_page_link = None
            
            for page_link in page_links:
                try:
                    page_num = int(page_link.text.strip())
                    if page_num == current_page + 1:
                        next_page_link = page_link
                        break
                except ValueError:
                    continue
            
            if next_page_link and next_page_link.is_displayed():
                try:
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_page_link)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", next_page_link)
                    print(f"Clicked on page number {current_page + 1}")
                    pagination_found = True
                    time.sleep(3)  # Wait for the page to load
                except Exception as e:
                    print(f"Error clicking page number link: {e}")
        
        # Strategy 3: Direct URL modification based on Naukri's pagination pattern
        if not pagination_found:
            current_url = driver.current_url
            url_parts = current_url.split('?')
            base_url = url_parts[0]
            query_params = url_parts[1] if len(url_parts) > 1 else ""
            
            # Extract base path from URL
            path_parts = base_url.split('/')
            job_path = path_parts[-1] if path_parts else ""
            
            # Construct new URL based on Naukri.com pattern
            if "-jobs" in job_path:
                # Check if URL already has a page number at the end (like "sales-jobs-2")
                if "-" in job_path and job_path.split("-")[-1].isdigit():
                    # Replace existing page number
                    job_segments = job_path.split("-")
                    current_page_num = int(job_segments[-1])
                    base_job_path = "-".join(job_segments[:-1])  # Get everything before page number
                    new_job_path = f"{base_job_path}-{current_page_num + 1}"
                    # Reconstruct the full URL
                    path_parts[-1] = new_job_path
                    new_url = "/".join(path_parts)
                else:
                    # No page number yet, add "-2" to the current URL
                    new_url = f"{base_url}-2"
            else:
                # Default case - just add "-2" to the URL
                new_url = f"{base_url}-2"
                
            # Re-add query parameters if they exist
            if query_params:
                new_url = f"{new_url}?{query_params}"
                
            print(f"Generated pagination URL: {new_url}")
            driver.get(new_url)
            print(f"Navigated to next page using URL: {new_url}")
            time.sleep(3)  # Wait for the page to load
            pagination_found = True
            
        return pagination_found
    except Exception as e:
        print(f"Error navigating to next page: {e}")
        return False

def extract_job_card_data(driver, config):
    """Extract data from job cards with 'Apply on company site' buttons using exact CSS selectors"""
    job_data = {
        "job_url": driver.current_url,
        "application_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "external_site",
        "external_application": True
    }
    
    try:
        # Extract job title using exact selector
        title_elements = driver.find_elements(By.CSS_SELECTOR, "h1.styles_jd-header-title__rZwM1")
        if title_elements:
            job_data["title"] = title_elements[0].text
            print(f"Extracted job title: {job_data['title']}")
        
        # Extract company name using exact selector
        company_elements = driver.find_elements(By.CSS_SELECTOR, "div.styles_jd-header-comp-name__MvqAI a")
        if company_elements:
            job_data["company"] = company_elements[0].text
            print(f"Extracted company name: {job_data['company']}")
            
        # Extract location using exact selector
        location_elements = driver.find_elements(By.CSS_SELECTOR, "span.styles_jhc__location__W_pVs a")
        if location_elements:
            job_data["location"] = location_elements[0].text
            print(f"Extracted location: {job_data['location']}")
        
        # Extract experience requirement using exact selector
        exp_elements = driver.find_elements(By.CSS_SELECTOR, "div.styles_jhc__exp__k_giM span")
        if exp_elements:
            job_data["experience"] = exp_elements[0].text
            print(f"Extracted experience: {job_data['experience']}")
            
        # Extract salary using exact selector
        salary_elements = driver.find_elements(By.CSS_SELECTOR, "div.styles_jhc__salary__jdfEC span")
        if salary_elements:
            job_data["salary"] = salary_elements[0].text
            print(f"Extracted salary: {job_data['salary']}")
            
        # Extract job stats (posted date, openings, applicants)
        stats_elements = driver.find_elements(By.CSS_SELECTOR, "span.styles_jhc__stat__PgY67")
        for stat in stats_elements:
            stat_text = stat.text.lower()
            if "posted:" in stat_text:
                job_data["posted_date"] = stat_text.replace("posted:", "").strip()
                print(f"Extracted posted date: {job_data['posted_date']}")
            elif "applicants:" in stat_text:
                job_data["applicants"] = stat_text.replace("applicants:", "").strip()
                print(f"Extracted applicants: {job_data['applicants']}")
            elif "openings:" in stat_text:
                job_data["openings"] = stat_text.replace("openings:", "").strip()
                print(f"Extracted openings: {job_data['openings']}")
                
        # Check for company site button
        company_site_buttons = driver.find_elements(By.CSS_SELECTOR, "button#company-site-button")
        job_data["has_company_site_button"] = len(company_site_buttons) > 0
        if job_data["has_company_site_button"]:
            print("Found 'Apply on company site' button")
        
        # Try to get job description if available
        try:
            # Look for both job description formats
            job_description_elements = driver.find_elements(By.CSS_SELECTOR, ".styles_job-desc-main__UqAH1, .job-desc")
            if job_description_elements:
                job_data["description"] = job_description_elements[0].text
                print(f"Extracted job description of length: {len(job_data['description'])}")
            else:
                # Try alternative selector
                job_description_elements = driver.find_elements(By.XPATH, 
                    "//section[contains(@class, 'job-desc') or contains(@class, 'description')]")
                if job_description_elements:
                    job_data["description"] = job_description_elements[0].text
                    print(f"Extracted job description with alternative selector of length: {len(job_data['description'])}")
        except Exception as e:
            print(f"Error extracting job description: {e}")
        
    except Exception as e:
        print(f"Error extracting job card data: {e}")
        
    return job_data

def handle_company_site_application(driver, job_url, config):
    """Handle job applications that require going to company site"""
    print("Handling job with 'Apply on company site' button")
    
    # Extract job card data first
    job_data = extract_job_card_data(driver, config)
    
    if not job_data.get("title") and not job_data.get("company"):
        print("Failed to extract essential job details. Trying alternative extraction.")
        # Try another extraction method
        try:
            # Extract from basic page elements
            job_header = driver.find_element(By.ID, "job_header")
            if job_header:
                # Try to get title
                title_elem = job_header.find_elements(By.CSS_SELECTOR, "h1")
                if title_elem:
                    job_data["title"] = title_elem[0].text
                    print(f"Extracted job title from header: {job_data['title']}")
                
                # Try to get company
                company_elem = job_header.find_elements(By.CSS_SELECTOR, "a[title*='Careers']")
                if company_elem:
                    job_data["company"] = company_elem[0].text
                    print(f"Extracted company from header: {job_data['company']}")
                
                # Try to get location
                location_elem = job_header.find_elements(By.CSS_SELECTOR, "span.styles_jhc__location__W_pVs")
                if location_elem:
                    job_data["location"] = location_elem[0].text
                    print(f"Extracted location from header: {job_data['location']}")
        except Exception as e:
            print(f"Error with alternative extraction: {e}")
    
    # Check if job matches preferences before proceeding
    try:
        # If we have enough data to check preferences
        if job_data.get("title") or job_data.get("description"):
            matches_preferences, match_reason = job_matches_preferences(driver, job_data, config)
            if not matches_preferences:
                print(f"External job doesn't match preferences: {match_reason}")
                # Log the skipped job
                job_data["status"] = "skipped"
                job_data["skip_reason"] = "preference_mismatch"
                job_data["skip_details"] = match_reason
                save_job_log(job_data, config)
                return False
            
            print(f"External job matches preferences: {match_reason}")
        else:
            print("Insufficient data to check job preferences. Proceeding anyway.")
    except Exception as e:
        print(f"Error during preference matching for external job: {e}")
    
    # Log the job data
    job_data["status"] = "external_site_matched"
    job_data["application_method"] = "external_site"
    save_job_log(job_data, config)
    
    # Check if we should click the company site button
    external_settings = config.get("external_application_settings", {})
    if not external_settings:
        # Default behavior if not configured
        external_settings = {"handle_external_redirects": False}
    
    if external_settings.get("handle_external_redirects", False):
        try:
            company_site_buttons = driver.find_elements(By.CSS_SELECTOR, "button#company-site-button")
            if company_site_buttons:
                for button in company_site_buttons:
                    if button.is_displayed():
                        print("Clicking 'Apply on company site' button")
                        driver.execute_script("arguments[0].click();", button)
                        time.sleep(5)  # Wait for navigation
                        
                        # Update job data with new URL
                        job_data["external_url"] = driver.current_url
                        job_data["status"] = "external_site_visited"
                        save_job_log(job_data, config)
                        return True
        except Exception as e:
            print(f"Error clicking company site button: {e}")
    
    return True  # Return true since we've processed this job

def extract_job_details(driver):
    """Extract basic job details from the job page"""
    job_details = {
        "job_url": driver.current_url,
        "application_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "title": "",
        "company": "",
    }
    
    # Check if the page is an HTML error page
    page_source = driver.page_source
    if is_html_response(page_source) and "splashscreen-container" in page_source:
        print("Detected HTML error page instead of job details")
        job_details["status"] = "failed"
        job_details["error_reason"] = "html_response"
        job_details["error_details"] = "Received HTML error page instead of job data"
        
        # Try to extract title from URL if available
        try:
            url_parts = driver.current_url.split('?')
            if len(url_parts) > 0 and "jobTitle=" in url_parts[0]:
                title_param = [p for p in url_parts[0].split('&') if p.startswith("jobTitle=")]
                if title_param:
                    job_details["title"] = title_param[0].replace("jobTitle=", "").replace("+", " ")
        except Exception as e:
            print(f"Error extracting title from URL: {e}")
        
        return job_details
    
    try:
        # Try to get job title
        title_elements = driver.find_elements(By.CSS_SELECTOR, "h1.jd-header-title")
        if title_elements:
            job_details["title"] = title_elements[0].text
    except Exception as e:
        print(f"Error extracting job title: {e}")
    
    try:
        # Try to get company name
        company_elements = driver.find_elements(By.CSS_SELECTOR, "div.jd-header-comp-name a")
        if company_elements:
            job_details["company"] = company_elements[0].text
    except Exception as e:
        print(f"Error extracting company name: {e}")
    
    return job_details

def extract_detailed_job_info(driver):
    """Extract detailed job information for preference matching"""
    job_info = extract_job_details(driver)
    
    # If already identified as an HTML error response, return early
    if job_info.get("status") == "failed" and job_info.get("error_reason") == "html_response":
        return job_info
    
    # Add job description
    try:
        job_description_elements = driver.find_elements(By.CSS_SELECTOR, "div.job-desc")
        if job_description_elements:
            job_info["description"] = job_description_elements[0].text
        else:
            # Try alternative selector
            job_description_elements = driver.find_elements(By.XPATH, "//section[contains(@class, 'job-desc')]")
            if job_description_elements:
                job_info["description"] = job_description_elements[0].text
            else:
                job_info["description"] = ""
    except Exception as e:
        print(f"Error extracting job description: {e}")
        job_info["description"] = ""
    
    # Add job requirements
    try:
        requirements_elements = driver.find_elements(By.CSS_SELECTOR, "div.key-skill")
        if requirements_elements:
            job_info["requirements"] = requirements_elements[0].text
        else:
            # Try alternative selector
            requirements_elements = driver.find_elements(By.XPATH, "//section[contains(@class, 'requirements')]")
            if requirements_elements:
                job_info["requirements"] = requirements_elements[0].text
            else:
                job_info["requirements"] = ""
    except Exception as e:
        print(f"Error extracting job requirements: {e}")
        job_info["requirements"] = ""
    
    # Add experience required
    try:
        exp_elements = driver.find_elements(By.CSS_SELECTOR, "span.exp")
        if exp_elements:
            job_info["experience"] = exp_elements[0].text
    except Exception as e:
        print(f"Error extracting experience requirement: {e}")
    
    # Add location
    try:
        location_elements = driver.find_elements(By.CSS_SELECTOR, "span.loc")
        if location_elements:
            job_info["location"] = location_elements[0].text
    except Exception as e:
        print(f"Error extracting job location: {e}")
    
    return job_info

def job_matches_preferences(driver, job_info, config):
    """Check if a job matches the user's preferences"""
    print("Evaluating job against your preferences...")
    
    # Get job preferences from config
    job_preferences = config.get("job_preferences", "")
    
    # Prepare prompt for AI
    prompt = f"""
    My job preferences:
    {job_preferences}
    
    Job details:
    Title: {job_info.get('title', 'Not specified')}
    Company: {job_info.get('company', 'Not specified')}
    Location: {job_info.get('location', 'Not specified')}
    Experience required: {job_info.get('experience', 'Not specified')}
    
    Description:
    {job_info.get('description', 'Not specified')}
    
    Requirements:
    {job_info.get('requirements', 'Not specified')}
    
    Based on the above information, does this job match my preferences?
    Please respond with 'yes' if it's a good match, or 'no' if it's not a good match.
    Also provide a brief reason in one sentence.
    """
    
    # Get response from AI
    response = bard_flash_response(prompt)
    print(f"AI response: {response}")
    
    # Parse the response
    match_decision = False
    match_reason = "No clear reason provided"
    
    if response.lower().startswith("yes"):
        match_decision = True
        match_reason = response
    elif " yes " in response.lower():
        match_decision = True
        match_reason = response
    else:
        match_reason = response
    
    # Log the decision
    match_data = {
        "job_url": job_info["job_url"],
        "job_title": job_info.get("title", "Not specified"),
        "company": job_info.get("company", "Not specified"),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "matches_preferences": match_decision,
        "ai_response": response
    }
    save_preference_match_log(match_data, config)
    
    return match_decision, match_reason

def get_safe_response(question, config):
    """Get a response that won't fail, with appropriate fallbacks"""
    if not question or question.strip() == "":
        # For empty questions, return a safe default answer
        return "Yes"
        
    try:
        response = bard_flash_response(question)
        if not response or len(response) < 1:
            return get_default_answer(question, config)
        return response
    except Exception as e:
        print(f"Error getting AI response: {e}")
        return get_default_answer(question, config)

def get_default_answer(question, config):
    """Get default answer based on question content"""
    question_lower = question.lower()
    default_answers = config.get("default_answers", {})
    
    if "notice" in question_lower or "joining" in question_lower:
        return default_answers.get("notice_period", "60 days")
    elif "salary" in question_lower or "ctc" in question_lower or "package" in question_lower:
        return default_answers.get("expected_salary", "18 LPA")
    elif "location" in question_lower or "city" in question_lower:
        return default_answers.get("current_location", "Noida") 
    elif "shift" in question_lower or "work hours" in question_lower or "timing" in question_lower:
        return "Flexible"
    elif "reason" in question_lower or "why" in question_lower:
        return default_answers.get("reason_for_job_change", "Growth opportunities")
    elif "date of birth" in question_lower or "dob" in question_lower:
        return config.get("date_formats", {}).get("dob", "06/12/2004")
    elif "willing to relocate" in question_lower:
        return "Yes"
    elif "preferred location" in question_lower:
        locations = default_answers.get("preferred_locations", ["Remote"])
        return locations[0] if locations else "Remote"
    elif "experience" in question_lower or "years" in question_lower:
        return "3.5 years"
    elif "skills" in question_lower or "technologies" in question_lower:
        return "Python, Django, Flask"
    
    # Default fallback
    return default_answers.get("generic_response", "Yes")

def handle_radio_buttons(driver, job_info, config):
    """Handle radio button questions during application"""
    wait = WebDriverWait(driver, 10)
    try:
        radio_buttons = WebDriverWait(driver, 1).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".ssrc__radio-btn-container"))
        )

        question = driver.find_element(By.XPATH, "//li[contains(@class, 'botItem')]/div/div/span").text
        print(question)

        options = []
        for index, button in enumerate(radio_buttons, start=1):
            label = button.find_element(By.CSS_SELECTOR, "label")
            value = button.find_element(By.CSS_SELECTOR, "input").get_attribute("value")
            options.append(f"{index}. {label.text} (Value: {value})")
            print(options[-1])

        options_str = "\n".join(options)
        user_input_message = f"{question}\n{options_str}"

        # Log the question and options
        question_data = {
            "job_url": driver.current_url,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "question_type": "multiple_choice",
            "question": question,
            "options": options,
            "job_title": job_info.get("title", ""),
            "company": job_info.get("company", "")
        }

        save_question_log(question_data, config)

        selected_option = int(bard_flash_response(user_input_message))

        selected_button = radio_buttons[selected_option - 1].find_element(By.CSS_SELECTOR, "input")
        driver.execute_script("arguments[0].click();", selected_button)

        save_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div/div[1]/div[3]/div/div")))
        save_button.click()

        success_message = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.XPATH,
                                           "//span[contains(@class, 'apply-message') and contains(text(), 'successfully applied')]")))
        if success_message:
            # Log successful application
            job_data = extract_job_details(driver)
            job_data["status"] = "success"
            job_data["application_method"] = "radio_buttons"
            save_job_log(job_data, config)
            return True

        return False
    except Exception as e:
        print(f"Error handling radio buttons: {e}")
        return False

def handle_text_input(driver, job_info, config):
    """Handle text input questions during application"""
    wait = WebDriverWait(driver, 10)
    
    # Track if we're in a multi-question sequence
    in_qa_sequence = True
    question_count = 0
    max_sequential_questions = 15  # Safety limit to prevent infinite loops
    
    while in_qa_sequence and question_count < max_sequential_questions:
        question_count += 1
        print(f"Processing Q&A round {question_count}")
        
        try:
            # Try to find the chat list - wait a bit longer for it to appear
            chat_list = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.XPATH, "//ul[contains(@id, 'chatList_')]"))
            )
    
            # Extract the latest question text
            last_question_text = None
            li_elements = chat_list.find_elements(By.TAG_NAME, "li")
            
            if li_elements:
                # Get the last element that's likely to be a question
                # For each round, count from the end backward until we find a question
                # that hasn't been answered yet
                for idx in range(len(li_elements) - 1, -1, -1):
                    li_element = li_elements[idx]
                    
                    # Skip system messages or already answered questions
                    if "userItem" in li_element.get_attribute("class"):
                        continue  # Skip user responses
                        
                    # Try multiple ways to extract the text
                    try:
                        # Try to get text from span elements first (usually contains the formatted question)
                        spans = li_element.find_elements(By.TAG_NAME, "span")
                        if spans:
                            candidate_text = spans[0].text
                            if candidate_text and candidate_text.strip():
                                last_question_text = candidate_text
                                break
                                
                        # If that failed, try getting the text directly from the li element
                        if not last_question_text:
                            candidate_text = li_element.text
                            if candidate_text and candidate_text.strip():
                                last_question_text = candidate_text
                                break
                                
                        # If we still don't have text, try to find any visible text element
                        if not last_question_text:
                            text_elements = li_element.find_elements(By.XPATH, ".//*[text()]")
                            for element in text_elements:
                                if element.text and element.text.strip():
                                    last_question_text = element.text
                                    break
                            if last_question_text:
                                break
                    except Exception as e:
                        print(f"Error extracting question text from element: {e}")
                
                # If we couldn't find a new question, we might be done with the Q&A sequence
                if not last_question_text:
                    print("No new questions found. Q&A sequence may be complete.")
                    
                    # Check if we have at least answered some questions
                    if question_count > 1:
                        in_qa_sequence = False
                        continue
                    else:
                        # If this is the first attempt and we found no question, try a different approach
                        try:
                            # Try a broader search for any visible question-like text
                            question_elements = driver.find_elements(By.XPATH, 
                                "//*[contains(@class, 'question') or contains(@class, 'chatbot') or contains(@class, 'botItem')]")
                            
                            for elem in question_elements:
                                if elem.is_displayed() and elem.text and elem.text.strip():
                                    last_question_text = elem.text
                                    break
                        except Exception as e:
                            print(f"Error in broad question search: {e}")
            else:
                print("No chat list elements (<li>) found.")
                in_qa_sequence = False
                return False
    
            # Log what we found
            if last_question_text and last_question_text.strip():
                print(f"Question {question_count}: {last_question_text}")
                
                # Log the question
                question_data = {
                    "job_url": driver.current_url,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "question_type": "text_input",
                    "question": last_question_text,
                    "question_number": question_count,
                    "job_title": job_info.get("title", ""),
                    "company": job_info.get("company", "")
                }
                save_question_log(question_data, config)
            else:
                print(f"Warning: Empty question text for question {question_count}")
                if question_count > 1:
                    # If this is not the first question and it's empty, we're likely done
                    in_qa_sequence = False
                    continue
                
                # Use a default question for the first round if needed
                question_data = {
                    "job_url": driver.current_url,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "question_type": "text_input",
                    "question": "[Unknown question]",
                    "question_number": question_count,
                    "job_title": job_info.get("title", ""),
                    "company": job_info.get("company", "")
                }
                save_question_log(question_data, config)
                last_question_text = "Please provide a brief response"
    
            # Get response with a fallback for empty questions
            if not last_question_text or last_question_text.strip() == "":
                last_question_text = "Please provide a brief response"
                
            response = get_safe_response(last_question_text, config)
            print(f"AI response for question {question_count}: {response}")
            
            # Find and fill the input field
            try:
                # Try multiple selectors for input field
                input_selectors = [
                    "//div[@class='textArea']",
                    "//div[contains(@class, 'textInput')]",
                    "//textarea",
                    "//input[@type='text']"
                ]
                
                input_field = None
                for selector in input_selectors:
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        for elem in elements:
                            if elem.is_displayed():
                                input_field = elem
                                break
                        if input_field:
                            break
                    except:
                        continue
                
                if not input_field:
                    print("Could not find input field. Q&A sequence may be complete.")
                    in_qa_sequence = False
                    
                    # Check for success indicators before giving up
                    success_indicators = [
                        "//span[contains(@class, 'apply-message') and contains(text(), 'successfully applied')]",
                        "//div[contains(@class, 'apply-status-header') and contains(@class, 'green')]",
                        "//*[contains(text(), 'Successfully applied')]",
                        "//*[contains(text(), 'Thank you for applying')]"
                    ]
                    
                    for indicator in success_indicators:
                        elements = driver.find_elements(By.XPATH, indicator)
                        if elements and any(e.is_displayed() for e in elements):
                            print(f"Success indicator found: {indicator}")
                            job_data = extract_job_details(driver)
                            job_data["status"] = "success"
                            job_data["application_method"] = "text_input_qa_sequence"
                            job_data["questions_answered"] = question_count - 1
                            save_job_log(job_data, config)
                            return True
                    
                    continue
                
                # Handle special cases
                if last_question_text and "Date of Birth" in last_question_text:
                    try:
                        dob_elements = driver.find_elements(By.XPATH, "//ul[contains(@id, 'dob__input-container')]")
                        if dob_elements:
                            dob = dob_elements[0]
                            dob.send_keys(config.get("date_formats", {}).get("dob", "06/12/2004"))
                            # Skip the regular input since we've handled it specially
                            input_field = None
                    except Exception as e:
                        print(f"Error handling DOB input: {e}")
                        # Fall back to normal input method
                
                # Fill in the response
                if input_field:
                    input_field.clear()  # Clear any existing text
                    input_field.send_keys(response)
                    time.sleep(1)
                
                # Click send/save button
                button_clicked = False
                try:
                    # Try multiple selectors for the submit button
                    button_selectors = [
                        "/html/body/div[2]/div/div[1]/div[3]/div/div",
                        "//button[contains(@class, 'send')]",
                        "//button[contains(@class, 'submit')]",
                        "//div[contains(@class, 'sendBtn')]",
                        "//button[text()='Send']",
                        "//button[text()='Submit']",
                        "//button[contains(@class, 'btn-primary')]"
                    ]
                    
                    for selector in button_selectors:
                        try:
                            buttons = driver.find_elements(By.XPATH, selector)
                            for button in buttons:
                                if button.is_displayed() and button.is_enabled():
                                    driver.execute_script("arguments[0].click();", button)
                                    print(f"Clicked button using selector: {selector}")
                                    button_clicked = True
                                    break
                            if button_clicked:
                                break
                        except:
                            continue
                        
                    if not button_clicked:
                        print("Could not find send/submit button")
                        
                except Exception as e:
                    print(f"Error clicking buttons: {e}")
                
                # Wait for next question or success message
                time.sleep(3)
                
                # Check for success message
                try:
                    success_indicators = [
                        "//span[contains(@class, 'apply-message') and contains(text(), 'successfully applied')]",
                        "//div[contains(@class, 'apply-status-header') and contains(@class, 'green')]",
                        "//*[contains(text(), 'Successfully applied')]",
                        "//*[contains(text(), 'Thank you for applying')]"
                    ]
                    
                    for indicator in success_indicators:
                        elements = driver.find_elements(By.XPATH, indicator)
                        if elements and any(e.is_displayed() for e in elements):
                            print(f"Success indicator found: {indicator}")
                            job_data = extract_job_details(driver)
                            job_data["status"] = "success"
                            job_data["application_method"] = "text_input_qa_sequence"
                            job_data["questions_answered"] = question_count
                            save_job_log(job_data, config)
                            return True
                except Exception as e:
                    print(f"Error checking success indicators: {e}")
                
                # If we don't see success yet, continue to next question
                print(f"Looking for next question after answering question {question_count}")
                
                # Short wait to allow next question to appear
                time.sleep(2)
                
            except Exception as e:
                print(f"Error in Q&A sequence at question {question_count}: {e}")
                # If we've answered at least one question successfully, consider it partial success
                if question_count > 1:
                    print("Q&A sequence partially completed")
                    return True
                return False
                
        except Exception as e:
            print(f"Error finding chat list or questions: {e}")
            # If we've answered at least one question, consider it a partial success
            if question_count > 1:
                print("Q&A sequence partially completed due to error")
                return True
            return False
    
    # If we've gone through multiple questions without finding a success indicator,
    # consider it a success since we've made progress
    if question_count > 1:
        print(f"Completed Q&A sequence with {question_count-1} questions answered")
        job_data = extract_job_details(driver)
        job_data["status"] = "success"
        job_data["application_method"] = "text_input_qa_sequence_completed"
        job_data["questions_answered"] = question_count - 1
        save_job_log(job_data, config)
        return True
        
    return False

def check_for_success_indicators(driver, job_info, config):
    """Check if any success indicators are present on the page"""
    try:
        success_indicators = [
            "//span[contains(@class, 'apply-message') and contains(text(), 'successfully applied')]",
            "//div[contains(@class, 'apply-status-header') and contains(@class, 'green')]",
            "//*[contains(text(), 'Successfully applied')]",
            "//*[contains(text(), 'Thank you for applying')]",
            "//*[contains(text(), 'application has been submitted')]"
        ]
        
        for indicator in success_indicators:
            elements = driver.find_elements(By.XPATH, indicator)
            if elements and any(e.is_displayed() for e in elements):
                print(f"Success indicator found: {indicator}")
                job_data = extract_job_details(driver)
                job_data["status"] = "success"
                job_data["application_method"] = "success_detection"
                save_job_log(job_data, config)
                return True
                
        # Also check page content
        page_text = driver.page_source.lower()
        success_phrases = ["successfully applied", "application submitted", "thank you for applying"]
        for phrase in success_phrases:
            if phrase in page_text:
                print(f"Success phrase found in page content: '{phrase}'")
                job_data = extract_job_details(driver)
                job_data["status"] = "success"
                job_data["application_method"] = "text_detection"
                save_job_log(job_data, config)
                return True
                
        return False
    except Exception as e:
        print(f"Error checking success indicators: {e}")
        return False

def process_job(driver, job_url, config):
    """Process a single job - check match, apply, handle questions"""
    job_error_count = 0
    
    try:
        # Check for "Apply on company site" button first
        company_site_buttons = driver.find_elements(By.CSS_SELECTOR, "button#company-site-button, button.styles_company-site-button__C_2YK")
        if company_site_buttons and len(company_site_buttons) > 0:
            print("Detected 'Apply on company site' button")
            return handle_company_site_application(driver, job_url, config)
        
        # Extract job information
        job_info = extract_detailed_job_info(driver)
        
        # Check if we got an HTML error response
        if job_info.get("status") == "failed":
            print(f"Failed to load job details: {job_info.get('error_details')}")
            save_job_log(job_info, config)
            return False
        
        # Check for "already applied" indicators
        already_applied_elements = driver.find_elements(By.ID, "already-applied")
        already_applied_texts = driver.find_elements(By.XPATH, 
            "//*[contains(text(), 'already applied') or contains(text(), 'Already Applied')]")
        
        if already_applied_elements or already_applied_texts:
            print("Already applied to this job. Skipping.")
            job_data = extract_job_details(driver)
            job_data["status"] = "success"
            job_data["application_method"] = "already_applied"
            save_job_log(job_data, config)
            return True
        
        # Check if job matches preferences
        try:
            matches_preferences, match_reason = job_matches_preferences(driver, job_info, config)
            
            if not matches_preferences:
                print(f"Job doesn't match preferences: {match_reason}")
                return False
            
            print(f"Job matches preferences: {match_reason}")
        except Exception as e:
            print(f"Error during preference matching: {e}")
            job_error_count += 1
            if job_error_count > 2:
                return False
        
        # Try to apply to the job
        try:
            apply_buttons = driver.find_elements(By.XPATH, "//*[text()='Apply']")
            if not apply_buttons:
                apply_buttons = driver.find_elements(By.XPATH, "//button[contains(@class, 'apply-button')]")
                
            if apply_buttons:
                for button in apply_buttons:
                    if button.is_displayed():
                        driver.execute_script("arguments[0].click();", button)
                        print("Clicked Apply button")
                        time.sleep(3)
                        break
                        
            # Check for immediate success message
            success_elements = driver.find_elements(By.XPATH, 
                "//span[contains(@class, 'apply-message') and contains(text(), 'successfully applied')]")
            
            if success_elements:
                print("Successfully applied immediately")
                job_data = extract_job_details(driver)
                job_data["status"] = "success"
                job_data["application_method"] = "direct_apply"
                save_job_log(job_data, config)
                return True
                
        except Exception as e:
            print(f"Error during initial apply attempt: {e}")
            job_error_count += 1
            if job_error_count > 2:
                return False
        
        # Handle the application process flow
        max_question_attempts = 10
        question_attempts = 0
        
        while question_attempts < max_question_attempts:
            question_attempts += 1
            
            # First try handling radio buttons
            try:
                if handle_radio_buttons(driver, job_info, config):
                    return True
            except Exception as e:
                print(f"Error handling radio buttons: {e}")
                job_error_count += 1
            
            # Then try handling text input (which now handles multiple questions)
            try:
                if handle_text_input(driver, job_info, config):
                    return True
            except Exception as e:
                print(f"Error handling text input: {e}")
                job_error_count += 1
            
            # Check for success indicators
            if check_for_success_indicators(driver, job_info, config):
                return True
            
            # If we've accumulated too many errors, give up
            if job_error_count > config.get("max_error_count_per_job", 2):
                print(f"Too many errors ({job_error_count}). Aborting application.")
                error_data = {
                    "job_url": job_url,
                    "application_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "title": job_info.get("title", ""),
                    "company": job_info.get("company", ""),
                    "status": "failed",
                    "error_reason": "too_many_errors",
                    "error_details": f"Encountered {job_error_count} errors during application process"
                }
                save_job_log(error_data, config)
                return False
                
            # Short pause between attempts
            time.sleep(2)
            
            # If no changes detected on page, we might be done or stuck
            # Check if there are any elements suggesting continuation
            continuation_elements = driver.find_elements(By.XPATH, 
                "//*[contains(@class, 'chat-item') or contains(@class, 'chatbot') or contains(@class, 'question')]")
                
            if not continuation_elements:
                # Check for any other success indicators we might have missed
                page_text = driver.page_source.lower()
                if "successfully" in page_text and "applied" in page_text:
                    print("Success message detected in page content")
                    job_data = extract_job_details(driver)
                    job_data["status"] = "success"
                    job_data["application_method"] = "text_detection"
                    save_job_log(job_data, config)
                    return True
                else:
                    # We're probably done with this application with no clear outcome
                    break
        
        # Fallback for ambiguous situations - if we made it through most questions without errors,
        # consider it successful
        if job_error_count <= 1 and question_attempts > 3:
            print("Application process completed with some interactions. Marking as success.")
            job_data = extract_job_details(driver)
            job_data["status"] = "success"
            job_data["application_method"] = "probable_success"
            save_job_log(job_data, config)
            return True
            
        # If we get here, the application was not successful
        print("Could not complete application process.")
        return False
        
    except Exception as e:
        print(f"Unhandled error in process_job: {e}")
        return False
