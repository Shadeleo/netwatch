# Contributing to NetWatch

Thank you for your interest in contributing to NetWatch! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and grow
- Report security issues privately

## Getting Started

### 1. Fork & Clone
```bash
git clone https://github.com/YOUR_USERNAME/netwatch.git
cd netwatch
git remote add upstream https://github.com/ORIGINAL_OWNER/netwatch.git
```

### 2. Create Branch
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

### 3. Install Dependencies
```bash
npm install
cd backend/python && pip install -r requirements.txt
cd ../..
```

### 4. Make Changes
Follow the project structure and coding standards.

### 5. Test Your Changes
```bash
# Run both services
npm start
cd backend/python && python api_server.py
```

### 6. Commit with Clear Messages
```bash
git commit -m "feat: Add new feature description"
git commit -m "fix: Resolve bug issue #123"
git commit -m "docs: Update README"
```

### 7. Push & Create PR
```bash
git push origin feature/your-feature-name
```

## Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style changes (formatting, semicolons, etc.)
- `refactor`: Code restructuring
- `perf`: Performance improvements
- `test`: Adding tests
- `chore`: Build process, dependencies

**Example:**
```
feat(anomaly-detection): Add DDoS pattern recognition

- Implement connection rate threshold checking
- Add algorithm documentation
- Closes #42
```

## Code Style

### Python
```python
# Use type hints
def analyze_packet(src_ip: str, dst_ip: str, protocol: str) -> Dict:
    pass

# Follow PEP 8
# 4 spaces indentation
# Max line length: 88
```

### JavaScript
```javascript
// Use const by default
const maxConnections = 50;

// Clear naming
const connectionManager = new ConnectionManager();

// Add JSDoc comments
/**
 * Process incoming alerts
 * @param {Array} alerts - Array of alert objects
 */
function processAlerts(alerts) {
}
```

## Pull Request Process

1. **Update README** if adding new features
2. **Add tests** if applicable
3. **Update documentation** in `/docs`
4. **Ensure no conflicts** with main branch
5. **Provide description** of changes

## Testing

Before submitting:

```bash
# Python: Check syntax
python -m py_compile backend/python/*.py

# JavaScript: Lint (if configured)
npm run lint

# Run services and verify functionality
```

## Documentation

- Update README.md for user-facing changes
- Update API documentation in `/docs`
- Add inline comments for complex logic
- Include usage examples when applicable

## Reporting Bugs

### Security Issues
⚠️ **Please don't open public issues for security vulnerabilities!**

Email: security@example.com with details.

### Other Issues
Include:
- Clear title describing the problem
- Steps to reproduce
- Expected vs. actual behavior
- System information (OS, Python version, Node version)
- Screenshots if applicable

## Feature Requests

Provide:
- Clear description of the feature
- Use cases and benefits
- Example implementation (if possible)
- Any related issues

## Questions?

- Open a discussion on GitHub
- Check existing issues/documentation
- Ask in pull request comments

---

Thank you for contributing to NetWatch! 🎉
