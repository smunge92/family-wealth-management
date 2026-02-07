# Contributing to Family Wealth Management

Thank you for your interest in contributing to Family Wealth Management! This document provides guidelines for contributing to the project.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally
3. **Set up your development environment** following the [README.md](README.md)
4. **Create a branch** for your changes

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Azure CLI
- Azure Functions Core Tools

### Local Development

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
func start

# Frontend (in a separate terminal)
cd frontend
npm install
npm start
```

### Environment Configuration

Copy the example files and fill in your own values:

```bash
# Backend
cp backend/local.settings.json.example backend/local.settings.json

# Frontend
cp frontend/.env.example frontend/.env
```

**Never commit files containing real API keys or secrets!**

## Code Style

### Python (Backend)
- Follow PEP 8 style guidelines
- Use type hints where possible
- Write docstrings for functions and classes
- Run `pytest tests/ -v` before submitting

### TypeScript/React (Frontend)
- Use functional components with hooks
- Follow the existing component structure
- Run `npm test` before submitting

## Submitting Changes

### Pull Request Process

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** and commit them:
   ```bash
   git add .
   git commit -m "Add feature: description of your changes"
   ```

3. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

4. **Open a Pull Request** on GitHub

### PR Guidelines

- Provide a clear description of what your changes do
- Reference any related issues
- Include screenshots for UI changes
- Ensure all tests pass
- Update documentation if needed

## Security

### Reporting Vulnerabilities

If you discover a security vulnerability, please:
1. **Do NOT** open a public issue
2. Email the maintainers directly with details
3. Allow time for a fix before public disclosure

### Code Security

- Never hardcode secrets, API keys, or passwords
- Use environment variables for configuration
- Validate all user input
- Follow OWASP security guidelines

## Areas for Contribution

### Good First Issues
- Documentation improvements
- Bug fixes
- Test coverage improvements
- UI/UX enhancements

### Feature Ideas
- Additional bank integrations
- New AI-powered insights
- Budgeting features
- Investment tracking improvements
- Mobile responsiveness
- Accessibility improvements

## Questions?

If you have questions, feel free to:
- Open a GitHub issue
- Check existing documentation
- Review closed issues for similar questions

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
