# Gitea Integration - User Guide

**Quick reference for using Gitea-integrated SciTeX Cloud**

---

## 🚀 Creating Projects

### Option 1: Create New Repository

1. Go to: http://localhost:8000/new
2. Fill in:
   - **Name:** "My Research Project" (can have spaces)
   - **Description:** Optional
3. Select: **"Create new"** (default)
4. Click **"Create Repository"**

**Result:**
- Repository created in Gitea
- Cloned to `./data/yourusername/my-research-project/`
- Ready to use with git commands

### Option 2: Import from GitHub/GitLab

1. Go to: http://localhost:8000/new
2. Fill in:
   - **Name:** "Imported Project"
   - **Description:** Optional
3. Select: **"Import from GitHub/GitLab"**
4. Enter **Repository URL** (both formats work):
   - HTTPS: `https://github.com/user/repo`
   - SSH: `git@github.com:user/repo.git`
5. For **private repos**, enter Access Token
6. Click **"Create Repository"**

**Result:**
- Repository migrated from GitHub to Gitea
- All history, branches preserved
- Cloned to local directory

---

## 📁 Working with Local Files

### Edit Files Locally
```bash
# Navigate to project
cd ./data/yourusername/my-project/

# Edit with any tool
vim README.md
code .
jupyter notebook

# Commit changes
git add .
git commit -m "Update analysis"
git push origin main
```

### View in Gitea
Open: http://localhost:3000/yourusername/my-project

---

## 🔑 GitHub Tokens

### For Public Repos
- No token needed!
- Just enter the URL

### For Private Repos
1. Go to: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes:
   - ✅ `repo` (full control of private repositories)
4. Generate and copy token
5. Paste in SciTeX import form

**Token format:**
- Classic: `ghp_xxxxxxxxxxxxx`
- Fine-grained: `github_pat_xxxxxxxxxxxxx`

---

## ⚠️ Common Issues

### "Repository with the same name already exists"
**Problem:** You already have a project with that slug in Gitea

**Solution:** Use a different name or delete the old project first

### "GitHub URL is required"
**Problem:** Forgot to enter the URL when selecting "Import"

**Solution:** Enter the repository URL in the field

### "Remote visit addressed rate limitation"
**Problem:** GitHub rate limiting (too many requests without token)

**Solution:** Provide a GitHub token (even for public repos)

---

## 📊 Repository Name vs Slug

When you create a project:
- **Display Name** (can have spaces): "My Research Project"
- **Repository Slug** (URL-safe): `my-research-project`

In Gitea:
- URL: `http://localhost:3000/username/my-research-project`
- Shown as: "My Research Project"

This is like GitHub - display names can be fancy, URLs are clean!

---

## ✅ Quick Checklist

Before importing from GitHub:
- [ ] Repository URL ready (HTTPS or SSH format)
- [ ] GitHub token ready (if private repo)
- [ ] Unique project name chosen
- [ ] Gitea running (`./deployment/gitea/start-dev.sh`)

After import:
- [ ] Check Gitea: http://localhost:3000
- [ ] Check local files: `cd ./data/yourusername/project-name`
- [ ] Try git commands: `git log`, `git status`

---

**Everything works! Start creating projects!** 🎉
