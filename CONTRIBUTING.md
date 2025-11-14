# Contributing to SCUM Server Manager

🎉 Thank you for your interest in contributing to SCUM Server Manager!

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Pull Request Process](#pull-request-process)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)

## 📜 Code of Conduct

This project and everyone participating in it is governed by respect, professionalism, and collaboration. By participating, you are expected to uphold this code.

## 🤝 How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates.

**Good Bug Reports Include:**
- Clear, descriptive title
- Detailed steps to reproduce
- Expected vs actual behavior
- Screenshots if applicable
- System information (OS, Python version)
- Error messages/logs

### Suggesting Features

Feature suggestions are welcome! Please:
- Use a clear, descriptive title
- Provide detailed description of the feature
- Explain why this feature would be useful
- Include mockups/examples if possible

### Code Contributions

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test thoroughly
5. Commit with clear messages
6. Push to your fork
7. Open a Pull Request

## 🛠️ Development Setup

### Prerequisites

- Python 3.8 or higher
- PySide6
- Git

### Installation

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/scum-server-manager.git
cd scum-server-manager

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python scum_server_manager_pyside.py
```

## 📝 Coding Standards

### Python Style

- Follow PEP 8 guidelines
- Use meaningful variable names
- Add docstrings to classes and functions
- Keep functions focused and small
- Comment complex logic

**Example:**

```python
def parse_log_entry(line: str) -> dict:
    """
    Parse a single log line into structured data.
    
    Args:
        line: Raw log line string
        
    Returns:
        Dictionary with parsed log data
        
    Raises:
        ValueError: If line format is invalid
    """
    # Implementation here
    pass
```

### Qt/PySide6 Guidelines

- Use proper signal/slot connections
- Clean up resources in `closeEvent`
- Keep UI logic separate from business logic
- Use layouts instead of absolute positioning
- Follow Qt naming conventions

### Documentation

- Update README.md for new features
- Add docstrings to new functions
- Update user guides as needed
- Include inline comments for complex code

## 🔄 Pull Request Process

### Before Submitting

1. **Test your changes**
   - Run the application
   - Test all affected features
   - Check for regressions

2. **Update documentation**
   - Update README if needed
   - Add/update docstrings
   - Update relevant guides

3. **Check code quality**
   - Remove debug code
   - Fix linting issues
   - Ensure proper formatting

### PR Guidelines

- Use clear, descriptive title
- Reference related issues (#123)
- Describe what changed and why
- Include screenshots for UI changes
- List any breaking changes

**PR Template:**

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How was this tested?

## Screenshots
(if applicable)

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings
- [ ] Tested thoroughly
```

## 🐛 Reporting Bugs

Use GitHub Issues with the bug report template:

**Title:** `[BUG] Short description`

**Body:**
```markdown
## Description
Clear description of the bug

## Steps to Reproduce
1. Go to '...'
2. Click on '...'
3. See error

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: [e.g., Windows 10]
- Python: [e.g., 3.10.5]
- PySide6: [e.g., 6.5.0]

## Additional Context
Any other relevant information

## Screenshots/Logs
(if applicable)
```

## 💡 Suggesting Features

Use GitHub Issues with the feature request template:

**Title:** `[FEATURE] Short description`

**Body:**
```markdown
## Problem
What problem does this solve?

## Proposed Solution
How should it work?

## Alternatives Considered
Other approaches you've thought about

## Additional Context
Mockups, examples, references
```

## 🎨 UI/UX Contributions

- Maintain consistent design language
- Ensure accessibility (keyboard navigation, contrast)
- Test on different screen sizes
- Follow Qt styling best practices
- Keep user experience intuitive

## 🧪 Testing

- Test on Windows (primary target)
- Test major features after changes
- Include error handling tests
- Test edge cases
- Verify RCON connectivity if applicable

## 📚 Documentation

Good documentation includes:
- What the code does
- Why it does it
- How to use it
- Known limitations
- Example usage

## 🏆 Recognition

Contributors will be:
- Listed in README.md
- Credited in release notes
- Acknowledged in commits

## 📞 Contact

- GitHub Issues: For bugs/features
- Discussions: For questions/ideas
- Pull Requests: For code contributions

## ⚖️ License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to SCUM Server Manager! 🚀
