# NetWatch — Git Setup & GitHub Deployment

## 📝 Initialize Git Repository

### Step 1: Initialize Git Locally

```bash
cd netwatch

# Initialize git repository
git init

# Configure your identity
git config user.name "Your Name"
git config user.email "your.email@example.com"

# Add all files
git add .

# Create initial commit
git commit -m "feat: Initial commit - NetWatch network monitor"

# Verify
git log --oneline
```

### Step 2: Create GitHub Repository

1. **Go to GitHub**: https://github.com/new
2. **Repository name**: `netwatch`
3. **Description**: `NetWatch — Real-time network monitor with anomaly detection`
4. **Visibility**: Choose Public or Private
5. **Do NOT initialize with README** (we already have one)
6. **Create Repository**

### Step 3: Push to GitHub

```bash
# Add remote repository
git remote add origin https://github.com/YOUR_USERNAME/netwatch.git

# Rename branch to main (if needed)
git branch -M main

# Push to GitHub
git push -u origin main

# Verify
git remote -v
```

## 🔄 Branching Strategy

We use GitHub Flow:

```
main (production)
 │
 └─ feature/new-feature
    └─ fix/bug-fix
    └─ docs/documentation
```

### Create Feature Branch

```bash
# Create from main
git checkout -b feature/your-feature-name

# Make changes...
git add .
git commit -m "feat: Your feature description"

# Push to GitHub
git push origin feature/your-feature-name

# Create Pull Request on GitHub
```

## 🚀 GitHub Actions CI/CD

The repository includes automated workflows. Push any code to trigger:

✅ **Python & Node.js tests**
✅ **Code linting**
✅ **Security scanning**
✅ **Automated builds**

View results in GitHub under "Actions" tab.

## 📦 Release Management

### Tag Releases

```bash
# Create version tag
git tag -a v1.0.0 -m "Release version 1.0.0"

# Push tags to GitHub
git push origin --tags

# View tags
git tag -l
```

### GitHub Releases

1. Go to "Releases" on GitHub
2. Click "Create a new release"
3. Tag: `v1.0.0`
4. Title: "NetWatch v1.0.0"
5. Description: Release notes
6. Publish release

## 📋 Commit Guidelines

### Format
```
<type>(<scope>): <subject>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code formatting
- `refactor`: Code restructuring
- `perf`: Performance improvement
- `test`: Tests
- `chore`: Maintenance

### Examples
```bash
git commit -m "feat(dashboard): Add real-time alert notifications"
git commit -m "fix(websocket): Resolve connection timeout issue"
git commit -m "docs(readme): Update installation instructions"
git commit -m "chore(deps): Update dependencies"
```

## 🔐 GitHub Secrets for Deployment

For automated deployment, add secrets in GitHub:

1. Settings → Secrets and variables → Actions
2. Add secrets:
   - `DEPLOY_HOST` - Server hostname
   - `DEPLOY_USER` - SSH username
   - `DEPLOY_KEY` - SSH private key

## 🐛 Workflow for Bug Fixes

```bash
# Create fix branch
git checkout -b fix/issue-description

# Make changes
git add .
git commit -m "fix: Description of fix"

# Create PR
git push origin fix/issue-description
```

## ✨ Workflow for Features

```bash
# Create feature branch
git checkout -b feature/feature-name

# Implement feature
git add .
git commit -m "feat: Description of feature"

# Push and create PR
git push origin feature/feature-name
```

## 🔄 Pull Request Process

1. **Create PR** with clear description
2. **Link related issues**: "Closes #123"
3. **Request review** from maintainers
4. **Address feedback**
5. **Squash and merge** when approved

## 📊 Repository Statistics

```bash
# View commits
git log --oneline

# View contributors
git shortlog -sn

# View branch info
git branch -vv

# View tag info
git tag -l -n
```

## 🚀 Deploy from GitHub

When code is merged to `main`, GitHub Actions automatically:
1. Runs tests
2. Builds artifacts
3. Deploys to production (if configured)

View status under "Actions" tab.

## 📚 Additional Resources

- GitHub Flow: https://guides.github.com/introduction/flow/
- Conventional Commits: https://www.conventionalcommits.org/
- Git Documentation: https://git-scm.com/doc

---

**Ready to push? Run:**
```bash
git push origin main
```

Happy coding! 🎉
