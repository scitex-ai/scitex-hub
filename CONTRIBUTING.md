# Contributing to SciTeX Cloud

Thank you for your interest in contributing to SciTeX Cloud! This document provides guidelines and instructions for contributing to this project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Coding Standards](#coding-standards)
- [Making Changes](#making-changes)
- [Submitting Changes](#submitting-changes)
- [Testing](#testing)
- [Documentation](#documentation)
- [Community](#community)

## Code of Conduct

We are committed to providing a welcoming and inspiring community for all. Please be respectful and constructive in your interactions.

### Our Standards

- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

## Getting Started

### Prerequisites

- Python 3.9+
- Docker and Docker Compose (for containerized development)
- Git
- Node.js and npm (for frontend development)

### Ways to Contribute

1. **Code Contributions**: Bug fixes, new features, performance improvements
2. **Documentation**: Improve docs, write tutorials, fix typos
3. **Bug Reports**: Report issues with detailed reproduction steps
4. **Feature Requests**: Suggest new features or enhancements
5. **Community Support**: Help other users in discussions and issues

## Development Setup

### Using Docker (Recommended)

```bash
# Clone the repository
git clone git@github.com:ywatanabe1989/scitex-cloud.git
cd scitex-cloud

# Start development environment
make start

# Access at http://localhost:8000
```

### Local Development

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install scitex[web,scholar,writer,dev]

# Setup environment variables
cp deployment/dotenvs/dotenv.example .env
# Edit .env with your settings

# Run migrations
python manage.py migrate

# Create test user
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

### Test User

For testing purposes, use:
- Username: `test-user`
- Password: `Password123!`

## Project Structure

```
scitex-cloud/
├── apps/                    # Django applications
│   ├── scholar_app/        # Literature discovery
│   ├── writer_app/         # Scientific writing
│   ├── console_app/           # Code analysis
│   ├── viz_app/            # Data visualization
│   ├── project_app/        # Repository management
│   ├── auth_app/           # Authentication
│   ├── public_app/         # Landing page
│   └── dev_app/            # Design system
├── config/                 # Django configuration
├── containers/             # Docker deployments
├── SECRET/                 # Environment files (gitignored)
├── static/                 # Frontend assets
└── templates/              # Base templates
```

### Directory Conventions

- **All Django apps must follow the `apps/XXX_app/` naming convention**
- **Never place files in the project root** (except standard files like README.md, LICENSE, etc.)
- **App-specific files must be within their app directory**
- **Environment files go in `SECRET/` directory** (gitignored)

## Coding Standards

### Python

- Follow [PEP 8](https://pep8.org/) style guide
- Use type hints where appropriate
- Write docstrings for all functions and classes
- Maximum line length: 88 characters (Black formatter)
- Use Django best practices

Example:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: ./apps/example_app/views.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
import logging

logger = logging.getLogger("scitex")

@login_required
def example_view(request) -> HttpResponse:
    """
    Example view function.

    Args:
        request: Django request object

    Returns:
        HttpResponse: Rendered template
    """
    context = {"example": "data"}
    return render(request, "example_app/example.html", context)
```

### TypeScript/JavaScript

- **Use TypeScript over JavaScript** for all new code
- Add `console.log` for debugging during development
- Remove or comment out debug logs before production
- Follow the central logging system conventions

### CSS

- **No inline styles** - Factor out all styles to CSS files
- **Single source of truth** - Each class should be defined in only one CSS file
- **Common vs App-specific**: Distinguish clearly
  - Common: `./static/css/`
  - App-specific: `./apps/XXX_app/static/XXX_app/css/`
- See `./static/css/CSS_RULES.md` for detailed guidelines

### HTML

- Use Django template partials for reusable components
- Keep templates organized and readable
- Follow consistent indentation (2 spaces)
- Use semantic HTML5 elements

## Making Changes

### Branch Naming

- `feature/short-description` - New features
- `fix/issue-description` - Bug fixes
- `refactor/component-name` - Code refactoring
- `docs/what-changed` - Documentation updates

### Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:

```bash
feat(scholar): Add multi-source literature search
fix(writer): Fix LaTeX compilation error handling
docs(contributing): Update development setup instructions
refactor(project): Reorganize project directory structure
```

### Development Workflow

1. **Fork and Clone**
   ```bash
   git clone git@github.com:YOUR_USERNAME/scitex-cloud.git
   cd scitex-cloud
   git remote add upstream git@github.com:ywatanabe1989/scitex-cloud.git
   ```

2. **Create a Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make Changes**
   - Write clear, readable code
   - Follow coding standards
   - Add/update tests
   - Update documentation

4. **Test Your Changes**
   ```bash
   make test                    # Run test suite
   make lint                    # Check code style
   ```

5. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat(module): Add new feature"
   ```

6. **Keep Updated**
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

7. **Push Changes**
   ```bash
   git push origin feature/your-feature-name
   ```

## Submitting Changes

### Pull Request Process

1. **Create Pull Request**
   - Go to GitHub and create a new PR
   - Use a clear, descriptive title
   - Fill out the PR template completely
   - Reference any related issues

2. **PR Description Should Include**
   - Summary of changes
   - Motivation and context
   - Screenshots (for UI changes)
   - Testing performed
   - Checklist of completed items

3. **PR Review**
   - Address reviewer feedback promptly
   - Make requested changes in new commits
   - Keep discussion focused and professional
   - Be open to suggestions

4. **Merge Requirements**
   - All tests must pass
   - Code review approval required
   - No merge conflicts
   - Documentation updated
   - Follows coding standards

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Refactoring
- [ ] Documentation update

## Testing
- [ ] Added/updated tests
- [ ] All tests pass
- [ ] Manual testing completed

## Screenshots (if applicable)
Add screenshots for UI changes

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings generated
```

## Testing

### Running Tests

```bash
# Run all tests
make test

# Run specific app tests
python manage.py test apps.scholar_app

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

### Writing Tests

- Write tests for all new features
- Maintain or improve code coverage
- Use Django's TestCase framework
- Follow AAA pattern (Arrange, Act, Assert)

Example:

```python
from django.test import TestCase
from django.contrib.auth.models import User

class ExampleTestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_example_feature(self):
        """Test example feature works correctly"""
        # Arrange
        expected = "result"

        # Act
        result = self.user.example_method()

        # Assert
        self.assertEqual(result, expected)
```

## Documentation

### Documentation Standards

- Write clear, concise documentation
- Include code examples
- Update docs with code changes
- Use proper markdown formatting
- Add docstrings to all public functions/classes

### Documentation Locations

- **README.md**: Project overview and quick start
- **CONTRIBUTING.md**: This file
- **docs/**: Detailed documentation
- **Inline comments**: Complex code explanations
- **Docstrings**: Function/class documentation

## Community

### Getting Help

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and general discussion
- **Email**: ywatanabe@scitex.ai for direct contact

### Reporting Issues

When reporting bugs, include:

1. **Description**: Clear description of the issue
2. **Steps to Reproduce**: Detailed steps to reproduce the bug
3. **Expected Behavior**: What should happen
4. **Actual Behavior**: What actually happens
5. **Environment**: OS, Python version, Docker version, etc.
6. **Screenshots**: If applicable
7. **Logs**: Relevant error messages or logs

### Feature Requests

When suggesting features:

1. **Use Case**: Describe the problem you're trying to solve
2. **Proposed Solution**: Your suggested implementation
3. **Alternatives**: Other approaches you've considered
4. **Additional Context**: Any other relevant information

## Recognition

Contributors are recognized in several ways:

- Listed on the [Contributors page](https://scitex.ai/contributors/)
- Mentioned in release notes for significant contributions
- Added to the GitHub contributors list automatically

## License

By contributing to SciTeX Cloud, you agree that your contributions will be licensed under the MIT License.

---

## Questions?

Don't hesitate to reach out if you have questions:

- Open a [GitHub Discussion](https://github.com/ywatanabe1989/scitex-cloud/discussions)
- Email: ywatanabe@scitex.ai

Thank you for contributing to SciTeX Cloud!

---

**Built by researchers, for researchers.**
