# Git Setup Instructions

## Initial Repository Setup

Follow these steps to create your GitHub repository:

### 1. Create GitHub Repository

1. Go to https://github.com
2. Click the **"+"** icon → **"New repository"**
3. Fill in:
   - **Repository name**: `scum-server-manager`
   - **Description**: `Professional SCUM game server management tool with 365+ settings, SQLiteStudio integration, and modern Qt GUI`
   - **Visibility**: Choose Public or Private
   - **DO NOT** initialize with README (we already have one)
4. Click **"Create repository"**

### 2. Initialize Local Git Repository

Open PowerShell in your project directory and run:

```powershell
# Navigate to project directory
cd C:\Users\micha\Desktop\SCUM

# Initialize git repository
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: SCUM Server Manager Pro v1.0.0

Features:
- 365+ server configuration settings
- SQLiteStudio Professional integration
- 8 pre-configured server presets
- Player management system
- RCON console
- Modern PySide6 GUI
- Comprehensive documentation"

# Add remote repository (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/scum-server-manager.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### 3. Verify Upload

1. Go to your repository: `https://github.com/YOUR_USERNAME/scum-server-manager`
2. You should see all your files
3. README.md should display on the homepage

### 4. Configure Repository Settings

On GitHub, go to your repository → **Settings**:

#### General
- ✅ Enable **Issues**
- ✅ Enable **Discussions** (for community questions)
- ✅ Enable **Wiki** (optional)

#### About Section (right sidebar on main page)
- **Description**: `Professional SCUM game server management tool with 365+ settings, SQLiteStudio integration, and modern Qt GUI`
- **Website**: (if you have one)
- **Topics**: Add tags like:
  - `scum`
  - `server-management`
  - `game-server`
  - `pyside6`
  - `qt`
  - `database-manager`
  - `rcon`
  - `python`

#### Features to Enable
- ✅ **Releases**: For version releases
- ✅ **Packages**: If you plan to publish
- ✅ **Environments**: For deployment

### 5. Create First Release

1. Go to **Releases** → **Create a new release**
2. Click **"Choose a tag"** → Type `v1.0.0` → **Create new tag**
3. **Release title**: `v1.0.0 - Initial Release`
4. **Description**:
```markdown
# 🎉 SCUM Server Manager Pro - Initial Release

## Features

### ✨ Core Features
- 🗄️ SQLiteStudio Professional with easy editing dialogs
- ⚙️ 365+ configurable server settings
- 📊 8 pre-configured server presets
- 📋 Player management (view, teleport, ban, kick)
- 💬 RCON console with auto-complete
- 📈 Real-time server monitoring
- 🎨 Professional dark theme UI

### 📚 Documentation
- Complete user guides (1,500+ lines)
- Quick start guide
- SQLiteStudio guide
- Configuration reference

### 🛠️ Technical
- Python 3.8+ support
- PySide6 Qt framework
- Cross-platform compatible
- Comprehensive error handling

## Installation

```powershell
pip install -r requirements.txt
python scum_server_manager_pyside.py
```

See [QUICK_START_GUIDE.md](QUICK_START_GUIDE.md) for details.

## What's Included

- Complete source code
- Documentation
- Example configurations
- Test suite
- License (MIT)
```
5. Click **"Publish release"**

### 6. Add Repository Badges

Add to your README.md (already included in updated version):

```markdown
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PySide6](https://img.shields.io/badge/PySide6-6.0+-green.svg)](https://pypi.org/project/PySide6/)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)
```

### 7. Update URLs in Files

Replace `YOUR_USERNAME` in these files with your actual GitHub username:
- README.md
- CONTRIBUTING.md
- CHANGELOG.md
- SECURITY.md

### 8. Regular Git Workflow

After initial setup, use these commands for updates:

```powershell
# Check status
git status

# Add changes
git add .

# Commit with message
git commit -m "Description of changes"

# Push to GitHub
git push

# Create new branch for features
git checkout -b feature/new-feature

# Merge branch
git checkout main
git merge feature/new-feature
```

### 9. Protect Main Branch

On GitHub → **Settings** → **Branches** → **Add rule**:
- Branch name pattern: `main`
- ✅ Require pull request reviews before merging
- ✅ Require status checks to pass
- ✅ Include administrators (optional)

## Quick Commands Reference

```powershell
# Clone repository
git clone https://github.com/YOUR_USERNAME/scum-server-manager.git

# Update from remote
git pull

# Create branch
git checkout -b branch-name

# Switch branches
git checkout branch-name

# Delete branch
git branch -d branch-name

# View branches
git branch -a

# View commit history
git log --oneline

# Undo last commit (keep changes)
git reset --soft HEAD~1

# Discard all local changes
git reset --hard HEAD
```

## GitHub Desktop Alternative

If you prefer a GUI:

1. Download **GitHub Desktop**: https://desktop.github.com/
2. Install and sign in
3. **File** → **Add Local Repository** → Select your folder
4. Click **"Publish repository"**
5. Use the GUI to commit, push, pull

## Troubleshooting

### Authentication Issues
```powershell
# Use Personal Access Token instead of password
# Generate at: GitHub → Settings → Developer settings → Personal access tokens
```

### Large Files
```powershell
# If you have files > 50MB, use Git LFS
git lfs install
git lfs track "*.db"
git add .gitattributes
```

### Rejected Push
```powershell
# Pull first, then push
git pull origin main --rebase
git push
```

## Next Steps

1. ✅ Create repository on GitHub
2. ✅ Push code with git commands above
3. ✅ Configure repository settings
4. ✅ Create first release
5. ✅ Update README with your username
6. ✅ Enable issues and discussions
7. ✅ Share with community!

---

Your repository will be at: `https://github.com/YOUR_USERNAME/scum-server-manager`

**Don't forget to replace `YOUR_USERNAME` with your actual GitHub username!**
