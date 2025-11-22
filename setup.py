#!/usr/bin/env python3
"""
AliceJobSeeker - Setup and Installation Helper
Helps users set up the application for first-time use
"""

import os
import sys
import json
import subprocess


def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("ERROR: Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✓ Python version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    return True


def install_dependencies():
    """Install required dependencies"""
    print("\nInstalling dependencies from requirements.txt...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to install dependencies: {e}")
        return False


def create_directories():
    """Create necessary directories"""
    print("\nCreating necessary directories...")
    
    directories = ['logs', 'resume', 'profile']
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✓ Created directory: {directory}")
        else:
            print(f"✓ Directory already exists: {directory}")
    
    # Create README in resume folder
    resume_readme = "resume/README.md"
    if not os.path.exists(resume_readme):
        with open(resume_readme, 'w') as f:
            f.write("# Resume Folder\n\n")
            f.write("Place your resume PDF file here.\n\n")
            f.write("The default filename should be `resume.pdf`, but you can configure\n")
            f.write("a different filename in `customization.json` under:\n")
            f.write("`resume_settings.default_resume_filename`\n")
        print(f"✓ Created: {resume_readme}")
    
    return True


def create_sample_config():
    """Create sample configuration file if it doesn't exist"""
    config_file = "customization.json"
    
    if os.path.exists(config_file):
        print(f"\n✓ Configuration file already exists: {config_file}")
        response = input("Do you want to view/edit it now? (yes/no): ")
        if response.lower() in ['yes', 'y']:
            print("\nPlease edit customization.json with your preferred text editor.")
            print("Key fields to configure:")
            print("  - job_search_url: Your Naukri.com search URL")
            print("  - gemini_api_key: Your Google Gemini API key")
            print("  - job_preferences: Your job preferences")
            print("  - default_answers: Your default answers for common questions")
        return True
    
    print(f"\nConfiguration file not found. Creating sample: {config_file}")
    
    sample_config = {
        "job_search_url": "https://www.naukri.com/your-search-url-here",
        "page_load_wait_time": 5,
        "max_applications": 50,
        "max_jobs_to_process": 100,
        "max_error_count_per_job": 2,
        "log_directory": "logs",
        "max_retries": 3,
        "gemini_api_key": "YOUR_GEMINI_API_KEY_HERE",
        
        "resume_settings": {
            "use_pdf_resume": True,
            "resume_folder": "./resume",
            "default_resume_filename": "resume.pdf",
            "fallback_to_json_data": True,
            "parsing_confidence_threshold": 0.8
        },
        
        "browser_settings": {
            "profile_directory": "profile",
            "chrome_options": [
                "--start-maximized",
                "--disable-notifications",
                "--disable-popup-blocking"
            ],
            "take_screenshots": True
        },
        
        "preferences": {
            "auto_fill": True,
            "notification_enabled": True,
            "job_sites": ["naukri.com"],
            "max_retry_attempts": 3
        },
        
        "gemini_settings": {
            "model_name": "gemini-1.5-flash",
            "preference_model_name": "gemini-1.5-flash",
            "generation_config": {
                "temperature": 1,
                "top_p": 0.95,
                "top_k": 64,
                "max_output_tokens": 1000,
                "response_mime_type": "text/plain"
            },
            "preference_generation_config": {
                "temperature": 0.2,
                "top_p": 0.95,
                "top_k": 64,
                "max_output_tokens": 100,
                "response_mime_type": "text/plain"
            },
            "system_instruction": "remember all this when asked question you will answer from this data.\\nbe concise only answer in max 5 words, average of 2 words, min of 1 word\\n, if it is a multi option question only give the index number of the answer",
            "preference_system_instruction": "You are a job preference matching assistant. When comparing job descriptions with user preferences, only respond with 'yes' or 'no' followed by a brief one-sentence explanation. Be analytical and decisive in your assessment."
        },
        
        "job_preferences": "Describe your ideal job here (e.g., 'Software Engineer with Python and AI/ML experience')",
        
        "default_answers": {
            "notice_period": "60 days",
            "expected_salary": "10 LPA",
            "current_salary": "8 LPA",
            "current_location": "Your City",
            "preferred_locations": ["Remote", "Your City"],
            "reason_for_job_change": "Looking for better growth opportunities and challenging projects",
            "generic_response": "Yes"
        },
        
        "date_formats": {
            "dob": "01/01/1990",
            "job_application": "%Y-%m-%d %H:%M:%S"
        },
        
        "selenium_timeouts": {
            "default_wait": 2,
            "element_wait": 4,
            "page_load": 6,
            "between_actions": 1
        },
        
        "external_application_settings": {
            "handle_external_redirects": False
        }
    }
    
    try:
        with open(config_file, 'w') as f:
            json.dump(sample_config, f, indent=2)
        print(f"✓ Created sample configuration: {config_file}")
        print("\n⚠ IMPORTANT: Please edit customization.json and configure:")
        print("  1. job_search_url - Your Naukri.com job search URL")
        print("  2. gemini_api_key - Get it from https://makersuite.google.com/app/apikey")
        print("  3. job_preferences - Your job preferences")
        print("  4. default_answers - Your personal details and preferences")
        return True
    except Exception as e:
        print(f"ERROR: Failed to create configuration file: {e}")
        return False


def check_chrome():
    """Check if Chrome browser is installed"""
    print("\nChecking for Chrome browser...")
    try:
        # Try to import selenium and check for webdriver
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        
        print("✓ Chrome and Selenium are ready")
        print("  ChromeDriver will be downloaded automatically on first run")
        return True
    except ImportError:
        print("⚠ Selenium not installed yet - will be installed with dependencies")
        return True
    except Exception as e:
        print(f"⚠ Warning: {e}")
        print("  ChromeDriver will be downloaded automatically on first run")
        return True


def main():
    """Main setup function"""
    print("=" * 60)
    print("   AliceJobSeeker - Setup and Installation")
    print("=" * 60)
    print()
    
    # Check Python version
    if not check_python_version():
        return 1
    
    # Install dependencies
    print("\nStep 1: Installing Dependencies")
    print("-" * 40)
    if not install_dependencies():
        print("\n✗ Setup failed. Please fix the errors above.")
        return 1
    
    # Create directories
    print("\nStep 2: Creating Directories")
    print("-" * 40)
    if not create_directories():
        print("\n✗ Setup failed. Please fix the errors above.")
        return 1
    
    # Create configuration
    print("\nStep 3: Configuration")
    print("-" * 40)
    if not create_sample_config():
        print("\n✗ Setup failed. Please fix the errors above.")
        return 1
    
    # Check Chrome
    print("\nStep 4: Browser Check")
    print("-" * 40)
    check_chrome()
    
    # Final instructions
    print("\n" + "=" * 60)
    print("   Setup Complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Add your resume PDF to the 'resume' folder")
    print("  2. Edit 'customization.json' with your settings")
    print("  3. Get a Gemini API key from: https://makersuite.google.com/app/apikey")
    print("  4. Run health check: python cli.py --health-check")
    print("  5. Start the application: python cli.py")
    print()
    print("For help, run: python cli.py --help")
    print()
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nSetup interrupted by user. Exiting...")
        sys.exit(130)
    except Exception as e:
        print(f"\n✗ Setup failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
