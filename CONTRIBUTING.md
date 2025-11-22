# Contributing to AliceJobSeeker

Thank you for your interest in contributing to AliceJobSeeker! This document provides guidelines and instructions for contributing.

## 🤝 How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:
- A clear, descriptive title
- Steps to reproduce the bug
- Expected behavior
- Actual behavior
- Screenshots (if applicable)
- Your environment (OS, Python version, etc.)

### Suggesting Features

Feature suggestions are welcome! Please create an issue with:
- A clear description of the feature
- Use cases and benefits
- Any relevant examples or mockups

### Pull Requests

1. **Fork the repository** and create a new branch from `main`
2. **Make your changes** following our coding standards
3. **Test your changes** thoroughly
4. **Update documentation** if needed
5. **Submit a pull request** with a clear description

## 🏗️ Development Setup

1. Clone your fork:
```bash
git clone https://github.com/yourusername/AliceJobSeeker.git
cd AliceJobSeeker
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run setup:
```bash
python setup.py
```

## 📝 Coding Standards

### Python Style

- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Keep functions focused and single-purpose
- Maximum line length: 100 characters

### Documentation

- Update README.md for user-facing changes
- Add docstrings for all new functions
- Comment complex logic
- Update CHANGELOG.md

### Error Handling

- Use try-except blocks appropriately
- Provide helpful error messages
- Log errors with context
- Use retry mechanisms for transient failures

### Configuration

- Add new configuration options to customization.json
- Provide sensible defaults
- Document all configuration options
- Validate configuration on load

## 🧪 Testing

Before submitting a PR:

1. **Syntax Check**: Ensure all files compile
```bash
python -m py_compile *.py
```

2. **Manual Testing**: Test your changes manually
```bash
python cli.py --health-check
```

3. **Check Documentation**: Verify README and docstrings are updated

## 📂 Project Structure

```
AliceJobSeeker/
├── cli.py                 # Command-line interface
├── main.py                # Main application entry point
├── setup.py               # Setup and installation script
├── gemini_api.py          # Gemini AI integration
├── job_processor.py       # Job processing logic
├── selenium_utils.py      # Selenium/browser utilities
├── resume_parser.py       # Resume parsing logic
├── logger.py              # Logging utilities
├── utils.py               # Common utility functions
├── customization.json     # Configuration file
├── requirements.txt       # Python dependencies
├── README.md              # User documentation
├── CONTRIBUTING.md        # This file
├── logs/                  # Application logs
├── resume/                # Resume files
└── profile/               # Browser profile data
```

## 🎯 Areas Needing Help

We especially welcome contributions in these areas:

### High Priority
- [ ] Unit tests and test coverage
- [ ] LinkedIn integration
- [ ] Dry-run mode implementation
- [ ] Enhanced error recovery
- [ ] Performance optimizations

### Medium Priority
- [ ] Web dashboard UI
- [ ] Email notifications
- [ ] Multi-language support
- [ ] Additional job sites (Indeed, Glassdoor, etc.)
- [ ] Mobile app

### Low Priority
- [ ] Advanced analytics
- [ ] Application templates
- [ ] Calendar integration
- [ ] Interview scheduling

## 💡 Development Tips

### Working with Selenium

- Always use WebDriverWait instead of time.sleep()
- Handle stale element exceptions
- Use explicit waits over implicit waits
- Close browser sessions properly

### Working with Gemini API

- Use lazy initialization pattern
- Implement retry logic
- Handle rate limiting
- Cache responses when appropriate

### Configuration Best Practices

- Validate all configuration on load
- Provide helpful error messages
- Use sensible defaults
- Document all options

## 🐛 Common Issues

### ChromeDriver Issues
- Ensure Chrome browser is installed
- ChromeDriver is downloaded automatically via webdriver-manager
- Check browser version compatibility

### API Key Issues
- Get API key from https://makersuite.google.com/app/apikey
- Add to customization.json or environment variable
- Check API quotas and limits

### Import Errors
- Ensure all dependencies are installed
- Use virtual environment
- Check Python version (3.8+)

## 📋 Pull Request Checklist

Before submitting your PR, ensure:

- [ ] Code follows project style guidelines
- [ ] All files compile without errors
- [ ] Documentation is updated
- [ ] Changes are tested manually
- [ ] Commit messages are clear and descriptive
- [ ] PR description explains what and why
- [ ] No unnecessary files are included
- [ ] Secrets/API keys are not committed

## 🔄 Git Workflow

1. Create a feature branch:
```bash
git checkout -b feature/your-feature-name
```

2. Make your changes and commit:
```bash
git add .
git commit -m "Description of your changes"
```

3. Push to your fork:
```bash
git push origin feature/your-feature-name
```

4. Create a Pull Request on GitHub

## 📞 Getting Help

- Create an issue for questions
- Check existing issues and PRs
- Read the README.md thoroughly
- Run `python cli.py --health-check`

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🙏 Thank You!

Thank you for contributing to AliceJobSeeker! Your efforts help make job searching easier for everyone.
