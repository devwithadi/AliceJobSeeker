<div align="center">

# 🤖 AliceJobSeeker

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Selenium](https://img.shields.io/badge/Selenium-4.0+-green.svg)](https://www.selenium.dev/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status](https://img.shields.io/badge/Status-Active-success.svg)](https://github.com/devwithadi/AliceJobSeeker)

**Your AI-powered job application assistant that automates the boring parts of job hunting**

</div>

## ✨ Features

- 🔍 **Automated Job Discovery** - Find jobs matching your preferences automatically
- ✅ **Smart Filtering** - AI-powered job preference matching using Google Gemini
- 🤝 **Automated Applications** - Handle job applications with dynamic Q&A
- 📊 **Detailed Logging** - Keep track of all applications and their status
- 🔄 **Resume Parsing** - Automatically extract data from your resume (PDF support)
- 🌐 **Multi-site Support** - Currently supports Naukri.com (with more coming soon!)
- 💻 **CLI Interface** - User-friendly command-line interface with health checks
- 📈 **Statistics Dashboard** - Track your application success rates

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Chrome browser
- Gemini API key (for AI-powered features) - [Get it here](https://makersuite.google.com/app/apikey)

### Installation

1. **Clone the repository:**

```bash
git clone https://github.com/devwithadi/AliceJobSeeker.git
cd AliceJobSeeker
```

2. **Run the setup script:**

```bash
python setup.py
```

This will:
- Install all required dependencies
- Create necessary directories (logs, resume, profile)
- Generate a sample configuration file

3. **Configure your settings:**
   - Add your resume PDF to the `./resume/` folder
   - Edit `customization.json` with your preferences and API key

4. **Verify your setup:**

```bash
python cli.py --health-check
```

5. **Start applying to jobs:**

```bash
python cli.py
```

## 💻 Command Line Interface

AliceJobSeeker now includes a powerful CLI with multiple options:

```bash
# Show all available commands
python cli.py --help

# Run health check before starting
python cli.py --health-check

# View statistics from previous runs
python cli.py --stats

# Create a sample configuration file
python cli.py --init-config

# Limit applications (overrides config)
python cli.py --max-apps 10

# Use a custom configuration file
python cli.py --config my_config.json
```

## ⚙️ Configuration

AliceJobSeeker is highly customizable through `customization.json`. Here are the key settings:

### Essential Configuration

```json
{
  "job_search_url": "https://www.naukri.com/your-job-search-url",
  "gemini_api_key": "YOUR_API_KEY_HERE",
  "job_preferences": "Your ideal job description",
  "max_applications": 50
}
```

### Complete Configuration Options

```json
{
  "job_search_url": "Your Naukri.com search URL",
  "page_load_wait_time": 5,
  "max_applications": 500,
  "max_jobs_to_process": 500,
  "max_error_count_per_job": 2,
  "log_directory": "logs",
  "max_retries": 3,
  "gemini_api_key": "YOUR_API_KEY",
  
  "resume_settings": {
    "use_pdf_resume": true,
    "resume_folder": "./resume",
    "default_resume_filename": "resume.pdf",
    "fallback_to_json_data": true
  },
  
  "browser_settings": {
    "profile_directory": "profile",
    "chrome_options": ["--start-maximized", "--disable-notifications"]
  },
  
  "job_preferences": "Your job preferences here",
  
  "default_answers": {
    "notice_period": "60 days",
    "expected_salary": "10 LPA",
    "current_salary": "8 LPA",
    "current_location": "Your City",
    "preferred_locations": ["Remote", "Your City"],
    "reason_for_job_change": "Growth opportunities"
  },
  
  "external_application_settings": {
    "handle_external_redirects": false
  }
}
```

## 📝 How It Works

1. **Discovery**: AliceJobSeeker navigates to job search pages and finds job listings
2. **Filtering**: Uses AI to determine if jobs match your preferences
3. **Application**: For matching jobs, it attempts to apply automatically
4. **Q&A**: Handles application questions using AI, with fallbacks to predefined answers
5. **Logging**: Records all activities with detailed statistics

## 🐛 Bug Fixes in Latest Version

- ✅ Fixed critical crash when Gemini API key is missing (now uses lazy initialization)
- ✅ Added missing PDF parsing dependencies (PyPDF2, pdfplumber)
- ✅ Improved error handling throughout the application
- ✅ Added configuration validation on startup
- ✅ Fixed potential crashes with external application settings
- ✅ Better handling of browser session errors

## 🆕 What's New

### Version 1.1 Features

- 💻 **New CLI Interface** with health checks and statistics
- 📊 **Statistics Dashboard** to track application success rates
- 🔧 **Setup Script** for easy first-time configuration
- ✅ **Configuration Validation** to catch issues before running
- 📝 **Improved Logging** with better error messages
- 🛡️ **Better Error Recovery** with retry mechanisms

## 🛣️ Roadmap & TODO

### Completed ✅
- [x] CLI interface with health checks and statistics
- [x] Configuration validation
- [x] Lazy initialization for Gemini API
- [x] Resume parsing with PDF support
- [x] Comprehensive error handling
- [x] Setup script for easy installation

### In Progress 🚧
- [ ] **Dry-run Mode**: Preview jobs without applying
- [ ] **Enhanced Statistics**: More detailed analytics and visualizations
- [ ] **Unit Tests**: Comprehensive test coverage

### Planned Features 📋
- [ ] **LinkedIn Integration**: Job discovery and application on LinkedIn
- [ ] **Instahyre Support**: Expand to Instahyre's job application process
- [ ] **Multi-language Resume Support**: Parse resumes in different languages
- [ ] **Enhanced AI Matching**: Improve job preference matching algorithm
- [ ] **Web Dashboard**: Create a web-based interface for monitoring
- [ ] **Mobile Notifications**: Receive alerts about successful applications
- [ ] **Email Reports**: Daily/weekly summary reports via email
- [ ] **Application Templates**: Save and reuse application responses

## 🔧 Troubleshooting

### Common Issues

**Issue**: "No Gemini API key found"
- **Solution**: Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey) and add it to `customization.json`

**Issue**: "ChromeDriver not found"
- **Solution**: ChromeDriver is downloaded automatically on first run. Ensure you have Chrome browser installed.

**Issue**: "Resume not found"
- **Solution**: Add your resume PDF to the `resume` folder. Default name is `resume.pdf`

**Issue**: "Configuration file not found"
- **Solution**: Run `python cli.py --init-config` to create a sample configuration

**Issue**: Application is not working
- **Solution**: Run `python cli.py --health-check` to diagnose issues

### Getting Help

If you encounter issues:
1. Run the health check: `python cli.py --health-check`
2. Check the logs in the `logs` directory
3. Review the error messages carefully
4. Check if your configuration is valid
5. Open an issue on GitHub with details

## 👥 Contribution

Contributions are much awaited and highly appreciated! Here's how you can contribute:

1. Fork the repository
2. Create your feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature-name`
5. Open a pull request

Areas especially looking for help:
- Additional job site integrations
- UI/UX improvements
- Test coverage
- Documentation

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgements

- Selenium WebDriver
- Google Gemini API
- PyPDF2 and pdfplumber for resume parsing
- All our amazing contributors!

---

<div align="center">

**Made with ❤️**

</div>
