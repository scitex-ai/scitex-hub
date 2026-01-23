# Manual Testing Guide - Gitea Integration

**Complete testing checklist for the web UI**

---

## ✅ Prerequisites

- [ ] Gitea running: `docker ps | grep gitea` shows running
- [ ] Django running: Visit http://127.0.0.1:8000
- [ ] Logged in as: `ywatanabe`

---

## Test 1: Create New Repository

**URL:** http://127.0.0.1:8000/new/

**Steps:**
1. Enter **Name:** "Manual Test 1"
2. Enter **Description:** "Testing create new"
3. Select: **"Create new"** (should be selected by default)
4. Click **"Create Repository"**

**Expected Result:**
- ✅ Redirects to project page: `/ywatanabe/manual-test-1/`
- ✅ Shows message: "Project created in Git repository"
- ✅ Repository visible in Gitea: http://localhost:3000/scitex/manual-test-1
- ✅ Local directory created: `./data/ywatanabe/manual-test-1/`
- ✅ Contains git repository (has `.git` folder)

**If it fails:**
- What error message appears?
- Does it redirect? Where?
- Check browser console (F12) for JavaScript errors

---

## Test 2: Import from GitHub (Public Repo)

**URL:** http://127.0.0.1:8000/new/

**Steps:**
1. Enter **Name:** "Spoon Knife"
2. Select: **"Import from GitHub/GitLab"**
3. Enter **Repository URL:** `https://github.com/octocat/Spoon-Knife`
4. Leave **Access Token** empty (public repo)
5. Click **"Create Repository"**

**Expected Result:**
- ✅ Shows importing message (may take 10-30 seconds)
- ✅ Redirects to: `/ywatanabe/spoon-knife/`
- ✅ Message: "Project imported from GitHub"
- ✅ Gitea shows: http://localhost:3000/scitex/spoon-knife
- ✅ Local files: `./data/ywatanabe/spoon-knife/`

**If it fails with "rate limit":**
- This is expected for public imports without token
- Try with a GitHub token in profile settings

---

## Test 3: Import from GitHub (Private Repo with Saved Token)

**Setup:** First save token in profile
1. Go to: http://127.0.0.1:8000/profile/settings/
2. Scroll to **"Git Platform Integration"**
3. Enter **GitHub Token:** `YOUR_GITHUB_TOKEN_HERE` (get from https://github.com/settings/tokens)
4. Click **"Save changes"**
5. Verify: Message "Profile updated successfully"

**Test Import:**
1. Go to: http://127.0.0.1:8000/new/
2. Enter **Name:** "My Private Test"
3. Select: **"Import from GitHub/GitLab"**
4. Enter **Repository URL:** `git@github.com:ywatanabe1989/test-private.git` (SSH format)
5. Leave **Access Token** empty (will use saved token)
6. Notice: Should show "✅ Using saved token from profile settings"
7. Click **"Create Repository"**

**Expected Result:**
- ✅ Imports successfully using saved token
- ✅ Works with SSH URL (auto-converted to HTTPS)
- ✅ No need to enter token again

---

## Test 4: Error Handling

**Test:** Try to import without URL

1. Go to: http://127.0.0.1:8000/new/
2. Enter **Name:** "Error Test"
3. Select: **"Import from GitHub/GitLab"**
4. Leave **Repository URL** empty
5. Click **"Create Repository"**

**Expected Result:**
- ✅ Error message: "Repository URL is required for importing"
- ✅ Stays on the form (doesn't redirect)
- ✅ Name and description preserved
- ✅ Can correct and resubmit

---

## Test 5: Duplicate Name

**Test:** Try to create with existing name

1. Go to: http://127.0.0.1:8000/new/
2. Enter **Name:** "Test Private Import" (already exists)
3. Click **"Create Repository"**

**Expected Result:**
- ✅ Error: "You already have a project named..."
- ✅ Stays on form
- ✅ Can choose different name

---

## Test 6: Local Git Workflow

**After creating a project:**

```bash
cd ./data/ywatanabe/manual-test-1/

# Check git status
git status

# Create a file
echo "# My Research" >> README.md

# Commit
git add .
git commit -m "Update README"

# Push to Gitea
git push origin main
```

**Expected Result:**
- ✅ All git commands work
- ✅ Push succeeds
- ✅ Changes visible in Gitea: http://localhost:3000/scitex/manual-test-1
- ✅ Changes visible in Django UI

---

## 🐛 Common Issues & Solutions

### Issue: "GitHub URL is required for importing"

**Cause:** Selected "Import" but didn't enter URL

**Solution:** Enter a URL or switch to "Create new"

### Issue: "Repository with the same name already exists"

**Cause:** Gitea already has a repo with that slug

**Solution:**
- Use different name, or
- Delete old repo in Gitea first

### Issue: Form redirects without creating project

**Possible causes:**
1. JavaScript error - Check browser console (F12)
2. Validation failing silently
3. CSRF token issue

**Debug:**
```bash
# Check Django logs
tail -f logs/app.log

# Or check console output where runserver is running
```

### Issue: Import hangs/times out

**Cause:** Large repository or network issues

**Solution:**
- Try smaller repo first
- Check Gitea logs: `docker logs scitex-gitea-dev`

---

## ✅ Success Checklist

After successful creation:
- [ ] Project appears in Gitea: http://localhost:3000
- [ ] Local directory exists: `./data/ywatanabe/project-slug/`
- [ ] Git commands work: `git status`, `git log`
- [ ] Can push changes: `git push origin main`
- [ ] Project visible in Django: http://127.0.0.1:8000/ywatanabe/

---

## 🚀 Quick Test Commands

```bash
# Check Gitea is running
docker ps | grep gitea

# Check Django is running
ps aux | grep "manage.py runserver"

# List projects in Gitea
curl -H "Authorization: token 6a341ae28db2a367dd337e25142640501e6e7918" \
  http://localhost:3000/api/v1/user/repos | python3 -m json.tool

# Check local directories
ls -la ./data/ywatanabe/
```

---

**Test each scenario and report back which ones work/fail!**

**Iterate to greatness!** 🚀
