"""
AliceJobSeeker - Utility Functions
Common utility functions used across the application
"""

import os
import json
import time
from datetime import datetime
from functools import wraps


def is_empty_string(value):
    """
    Check if a value is None, empty string, or whitespace only
    
    Args:
        value: Value to check
    
    Returns:
        True if empty, False otherwise
    """
    return value is None or (isinstance(value, str) and value.strip() == "")


def retry_on_exception(max_retries=3, delay=1, exceptions=(Exception,)):
    """
    Decorator to retry a function on exception
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
        exceptions: Tuple of exceptions to catch and retry on
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    if retries >= max_retries:
                        print(f"Max retries ({max_retries}) reached for {func.__name__}: {e}")
                        raise
                    print(f"Retry {retries}/{max_retries} for {func.__name__} after error: {e}")
                    time.sleep(delay)
        return wrapper
    return decorator


def safe_json_load(file_path, default=None):
    """
    Safely load JSON file with error handling
    
    Args:
        file_path: Path to JSON file
        default: Default value if file doesn't exist or is invalid
    
    Returns:
        Loaded JSON data or default value
    """
    if default is None:
        default = {}
    
    if not os.path.exists(file_path):
        return default
    
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Warning: Invalid JSON in {file_path}: {e}")
        return default
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}")
        return default


def safe_json_save(file_path, data):
    """
    Safely save JSON file with error handling
    
    Args:
        file_path: Path to JSON file
        data: Data to save
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create directory if it doesn't exist
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving JSON to {file_path}: {e}")
        return False


def get_timestamp(format_string="%Y-%m-%d %H:%M:%S"):
    """
    Get current timestamp in specified format
    
    Args:
        format_string: strftime format string
    
    Returns:
        Formatted timestamp string
    """
    return datetime.now().strftime(format_string)


def ensure_directory_exists(directory):
    """
    Ensure a directory exists, create if it doesn't
    
    Args:
        directory: Path to directory
    
    Returns:
        True if successful, False otherwise
    """
    try:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"Created directory: {directory}")
        return True
    except Exception as e:
        print(f"Error creating directory {directory}: {e}")
        return False


def sanitize_filename(filename, max_length=255):
    """
    Sanitize a filename by removing invalid characters
    
    Args:
        filename: Original filename
        max_length: Maximum length of filename
    
    Returns:
        Sanitized filename
    """
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Truncate if too long
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        name = name[:max_length - len(ext) - 1]
        filename = name + ext
    
    return filename


def format_duration(seconds):
    """
    Format duration in seconds to human-readable string
    
    Args:
        seconds: Duration in seconds
    
    Returns:
        Formatted duration string (e.g., "2h 30m 15s")
    """
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")
    
    return " ".join(parts)


def truncate_string(text, max_length=100, suffix="..."):
    """
    Truncate a string to a maximum length
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncated
    
    Returns:
        Truncated string
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def validate_url(url):
    """
    Validate if a string is a valid URL
    
    Args:
        url: URL string to validate
    
    Returns:
        True if valid, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
    
    # Basic URL validation
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        return False
    
    # Check for basic URL structure
    if '.' not in url:
        return False
    
    return True


def get_config_value(config, key_path, default=None):
    """
    Get a value from nested config dictionary using dot notation
    
    Args:
        config: Configuration dictionary
        key_path: Dot-separated path (e.g., "resume_settings.use_pdf_resume")
        default: Default value if key not found
    
    Returns:
        Value from config or default
    """
    keys = key_path.split('.')
    value = config
    
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    
    return value


def merge_configs(base_config, override_config):
    """
    Merge two configuration dictionaries
    
    Args:
        base_config: Base configuration
        override_config: Override configuration
    
    Returns:
        Merged configuration
    """
    merged = base_config.copy()
    
    for key, value in override_config.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            merged[key] = merge_configs(merged[key], value)
        else:
            merged[key] = value
    
    return merged


class ProgressTracker:
    """Track progress of operations with statistics"""
    
    def __init__(self, total=0):
        self.total = total
        self.completed = 0
        self.failed = 0
        self.start_time = time.time()
    
    def increment_completed(self):
        """Increment completed count"""
        self.completed += 1
    
    def increment_failed(self):
        """Increment failed count"""
        self.failed += 1
    
    def get_elapsed_time(self):
        """Get elapsed time in seconds"""
        return time.time() - self.start_time
    
    def get_success_rate(self):
        """Get success rate as percentage"""
        total_processed = self.completed + self.failed
        if total_processed == 0:
            return 0.0
        return (self.completed / total_processed) * 100
    
    def get_progress_percentage(self):
        """Get progress percentage"""
        if self.total == 0:
            return 0.0
        processed = self.completed + self.failed
        return (processed / self.total) * 100
    
    def get_estimated_time_remaining(self):
        """Get estimated time remaining in seconds"""
        if self.completed == 0:
            return None
        
        elapsed = self.get_elapsed_time()
        rate = self.completed / elapsed
        remaining = self.total - (self.completed + self.failed)
        
        if rate == 0:
            return None
        
        return remaining / rate
    
    def print_status(self):
        """Print current status"""
        elapsed = format_duration(self.get_elapsed_time())
        success_rate = self.get_success_rate()
        
        print(f"\n--- Progress Status ---")
        print(f"Completed: {self.completed}")
        print(f"Failed: {self.failed}")
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"Elapsed Time: {elapsed}")
        
        if self.total > 0:
            progress = self.get_progress_percentage()
            print(f"Progress: {progress:.1f}%")
            
            eta = self.get_estimated_time_remaining()
            if eta:
                print(f"ETA: {format_duration(eta)}")
        
        print("----------------------\n")


# Export all utility functions
__all__ = [
    'is_empty_string',
    'retry_on_exception',
    'safe_json_load',
    'safe_json_save',
    'get_timestamp',
    'ensure_directory_exists',
    'sanitize_filename',
    'format_duration',
    'truncate_string',
    'validate_url',
    'get_config_value',
    'merge_configs',
    'ProgressTracker'
]
