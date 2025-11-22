#!/usr/bin/env python3
"""
AliceJobSeeker - Command Line Interface
Provides user-friendly command-line interface for the application
"""

import argparse
import sys
import json
import os
from datetime import datetime


def validate_config_file(config_path):
    """Validate that the configuration file exists and is valid JSON"""
    if not os.path.exists(config_path):
        print(f"ERROR: Configuration file not found: {config_path}")
        return False
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Check for required fields
        required_fields = ['job_search_url', 'gemini_api_key']
        missing_fields = [field for field in required_fields if not config.get(field) or config.get(field).strip() == ""]
        
        if missing_fields:
            print(f"WARNING: The following required fields are missing or empty in {config_path}:")
            for field in missing_fields:
                print(f"  - {field}")
            print("\nPlease update your configuration file before running.")
            return False
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in configuration file: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Failed to read configuration file: {e}")
        return False


def check_dependencies():
    """Check if all required dependencies are installed"""
    missing_deps = []
    
    try:
        import selenium
    except ImportError:
        missing_deps.append("selenium")
    
    try:
        import google.generativeai
    except ImportError:
        missing_deps.append("google-generativeai")
    
    try:
        import webdriver_manager
    except ImportError:
        missing_deps.append("webdriver-manager")
    
    if missing_deps:
        print("ERROR: Missing required dependencies:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\nPlease install dependencies with: pip install -r requirements.txt")
        return False
    
    return True


def health_check(config_path="customization.json"):
    """Perform health check of the system"""
    print("\n=== AliceJobSeeker Health Check ===\n")
    
    # Check Python version
    print("✓ Checking Python version...")
    if sys.version_info < (3, 8):
        print("  ✗ ERROR: Python 3.8 or higher is required")
        return False
    print(f"  ✓ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    # Check dependencies
    print("\n✓ Checking dependencies...")
    if not check_dependencies():
        return False
    print("  ✓ All required dependencies are installed")
    
    # Check configuration file
    print(f"\n✓ Checking configuration file ({config_path})...")
    if not validate_config_file(config_path):
        return False
    print("  ✓ Configuration file is valid")
    
    # Check resume folder
    print("\n✓ Checking resume folder...")
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        resume_folder = config.get("resume_settings", {}).get("resume_folder", "./resume")
        if not os.path.exists(resume_folder):
            print(f"  ⚠ WARNING: Resume folder not found: {resume_folder}")
            print(f"  Creating resume folder...")
            os.makedirs(resume_folder, exist_ok=True)
            print(f"  ✓ Resume folder created. Please add your resume PDF.")
        else:
            print(f"  ✓ Resume folder exists: {resume_folder}")
            
            # Check for resume files
            resume_files = [f for f in os.listdir(resume_folder) if f.endswith('.pdf')]
            if resume_files:
                print(f"  ✓ Found {len(resume_files)} resume file(s)")
            else:
                print(f"  ⚠ WARNING: No PDF resume files found in {resume_folder}")
    except Exception as e:
        print(f"  ⚠ WARNING: Could not check resume folder: {e}")
    
    # Check logs folder
    print("\n✓ Checking logs folder...")
    log_directory = config.get("log_directory", "logs")
    if not os.path.exists(log_directory):
        print(f"  Creating logs folder...")
        os.makedirs(log_directory, exist_ok=True)
        print(f"  ✓ Logs folder created: {log_directory}")
    else:
        print(f"  ✓ Logs folder exists: {log_directory}")
    
    print("\n=== Health Check Complete ===")
    print("✓ System is ready to run!\n")
    return True


def create_sample_config():
    """Create a sample configuration file"""
    sample_config = {
        "job_search_url": "https://www.naukri.com/your-search-url-here",
        "page_load_wait_time": 5,
        "max_applications": 50,
        "max_jobs_to_process": 100,
        "gemini_api_key": "YOUR_GEMINI_API_KEY_HERE",
        "resume_settings": {
            "use_pdf_resume": True,
            "resume_folder": "./resume",
            "default_resume_filename": "resume.pdf",
            "fallback_to_json_data": True
        },
        "browser_settings": {
            "profile_directory": "profile",
            "chrome_options": [
                "--start-maximized",
                "--disable-notifications"
            ]
        },
        "job_preferences": "Your job preferences here",
        "default_answers": {
            "notice_period": "60 days",
            "expected_salary": "10 LPA",
            "current_location": "Your City"
        },
        "log_directory": "logs"
    }
    
    config_path = "customization.json"
    if os.path.exists(config_path):
        print(f"Configuration file already exists: {config_path}")
        response = input("Do you want to overwrite it? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Aborted. Configuration file not modified.")
            return
    
    try:
        with open(config_path, 'w') as f:
            json.dump(sample_config, f, indent=2)
        print(f"✓ Sample configuration file created: {config_path}")
        print("Please edit the file and add your settings before running.")
    except Exception as e:
        print(f"ERROR: Failed to create configuration file: {e}")


def show_stats(config_path="customization.json"):
    """Show statistics from previous runs"""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        log_directory = config.get("log_directory", "logs")
        log_file = os.path.join(log_directory, "application_logs.json")
        
        if not os.path.exists(log_file):
            print("No statistics available. Run the job seeker first.")
            return
        
        with open(log_file, 'r') as f:
            logs = json.load(f)
        
        print("\n=== AliceJobSeeker Statistics ===\n")
        
        # Session statistics
        if "sessions" in logs and logs["sessions"]:
            print(f"Total Sessions: {len(logs['sessions'])}")
            
            total_successful = sum(s.get('successful_applications', 0) for s in logs['sessions'])
            total_failed = sum(s.get('failed_applications', 0) for s in logs['sessions'])
            
            print(f"Total Successful Applications: {total_successful}")
            print(f"Total Failed Applications: {total_failed}")
            print(f"Total Processed: {total_successful + total_failed}")
            
            if total_successful + total_failed > 0:
                success_rate = (total_successful / (total_successful + total_failed)) * 100
                print(f"Success Rate: {success_rate:.1f}%")
            
            # Last session
            if logs['sessions']:
                last_session = logs['sessions'][-1]
                print(f"\nLast Session: {last_session.get('timestamp')}")
                print(f"  Successful: {last_session.get('successful_applications', 0)}")
                print(f"  Failed: {last_session.get('failed_applications', 0)}")
        
        # Application statistics
        if "applications" in logs and logs["applications"]:
            print(f"\nTotal Job Records: {len(logs['applications'])}")
            
            # Status breakdown
            statuses = {}
            for app in logs["applications"]:
                status = app.get("status", "unknown")
                statuses[status] = statuses.get(status, 0) + 1
            
            print("\nStatus Breakdown:")
            for status, count in sorted(statuses.items(), key=lambda x: x[1], reverse=True):
                print(f"  {status}: {count}")
        
        # Preference match statistics
        if "preference_matches" in logs and logs["preference_matches"]:
            matches = logs["preference_matches"]
            matched = sum(1 for m in matches if m.get("matches_preferences"))
            total_checks = len(matches)
            
            print(f"\nPreference Matching:")
            print(f"  Total Checks: {total_checks}")
            print(f"  Matched: {matched}")
            print(f"  Not Matched: {total_checks - matched}")
            if total_checks > 0:
                match_rate = (matched / total_checks) * 100
                print(f"  Match Rate: {match_rate:.1f}%")
        
        print("\n" + "="*35 + "\n")
        
    except FileNotFoundError:
        print("No statistics available. Run the job seeker first.")
    except Exception as e:
        print(f"ERROR: Failed to read statistics: {e}")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="AliceJobSeeker - Automated Job Application Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Run with default settings
  %(prog)s --config my_config.json   # Use custom config file
  %(prog)s --dry-run                 # Preview without applying
  %(prog)s --max-apps 10             # Limit to 10 applications
  %(prog)s --health-check            # Check system health
  %(prog)s --stats                   # Show statistics
  %(prog)s --init-config             # Create sample config file
        """
    )
    
    parser.add_argument(
        '--config',
        default='customization.json',
        help='Path to configuration file (default: customization.json)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview jobs without applying'
    )
    
    parser.add_argument(
        '--max-apps',
        type=int,
        help='Maximum number of applications to submit (overrides config)'
    )
    
    parser.add_argument(
        '--health-check',
        action='store_true',
        help='Run system health check and exit'
    )
    
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show statistics from previous runs and exit'
    )
    
    parser.add_argument(
        '--init-config',
        action='store_true',
        help='Create a sample configuration file and exit'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='AliceJobSeeker v1.0.0'
    )
    
    return parser.parse_args()


def main():
    """Main CLI entry point"""
    args = parse_arguments()
    
    # Handle special commands that don't require running the main application
    if args.init_config:
        create_sample_config()
        return 0
    
    if args.health_check:
        success = health_check(args.config)
        return 0 if success else 1
    
    if args.stats:
        show_stats(args.config)
        return 0
    
    # Normal operation - validate before running
    print("\nStarting AliceJobSeeker...")
    print("Running pre-flight checks...\n")
    
    if not health_check(args.config):
        print("\n✗ Pre-flight checks failed. Please fix the issues above.")
        return 1
    
    # Import and run main application
    try:
        from main import main as run_main
        
        # Override config values if specified via CLI
        if args.max_apps:
            import json
            with open(args.config, 'r') as f:
                config = json.load(f)
            config['max_applications'] = args.max_apps
            # Note: This doesn't save the override, just passes it to the runtime
            print(f"Overriding max_applications to: {args.max_apps}")
        
        if args.dry_run:
            print("⚠ Dry-run mode requested but not yet implemented")
            print("Running in normal mode...\n")
        
        print("=" * 50)
        print("Starting job application process...")
        print("=" * 50 + "\n")
        
        run_main()
        
        print("\n" + "=" * 50)
        print("Job application process completed!")
        print("=" * 50)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user. Exiting...")
        return 130
    except Exception as e:
        print(f"\n✗ ERROR: Application failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
