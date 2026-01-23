<!-- ---
!-- Timestamp: 2025-10-19 03:03:23
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/deployment/gitea/GITEA_QUICKSTART.md
!-- --- -->

# Gitea Local Development - Quick Start

**Status:** ✅ Gitea is now running!

## Access Gitea

Open your browser and go to:
```
http://localhost:3000
```

## Initial Setup (First Time Only)

You'll see the installation wizard. Use these settings:

### Database Settings
- **Database Type:** SQLite3 (already selected)
- **Path:** /data/gitea/gitea.db (default)

### General Settings
- **Site Title:** SciTeX Git (or whatever you prefer)
- **Repository Root Path:** /data/git/repositories (default)
- **Git LFS Root Path:** /data/git/lfs (default)
- **Run As Username:** git (default)

### Server and Port Settings
- **SSH Server Domain:** localhost
- **SSH Port:** 22 (inside container, mapped to 2222 on host)
- **HTTP Port:** 3000
- **Gitea Base URL:** http://localhost:3000/

### Email Settings
- **Skip for now** (not needed for development)

### Administrator Account
Create your admin account:
- **Username:** scitex (or your preference)
- **Password:** Choose a secure password
- **Email:** your@email.com

**Click "Install Gitea"** and wait a few seconds.

## After Installation

### 1. Create Test Repository
- Click "+" (top right) → "New Repository"
- Name: `test-repo`
- Description: "Testing Gitea"
- Public/Private: Public
- Initialize: ☑ Add README
- Click "Create Repository"

### 2. Test Git Clone
```bash
git clone http://localhost:3000/admin/test-repo.git
cd test-repo
echo "# Test" >> README.md
git add .
git commit -m "Test commit"
git push origin main
```

### 3. Get API Token
For Django integration, you need an API token:
1. Click your avatar (top right) → Settings
2. Applications → Generate New Token
3. Token Name: "Django Integration"
4. Select scopes: (leave all checked for development)
5. Click "Generate Token"
6. **Copy the token** (you won't see it again!)

Save it as environment variable:
```bash
echo 'export GITEA_TOKEN="your_token_here"' >> ~/.bashrc
source ~/.bashrc
```

## Container Management

### Stop Gitea
```bash
docker stop scitex-gitea-dev
```

### Start Gitea
```bash
docker start scitex-gitea-dev
```

### View Logs
```bash
docker logs scitex-gitea-dev
```

### Remove Container (keeps data)
```bash
docker rm scitex-gitea-dev
```

### Remove Everything (including data)
```bash
docker rm scitex-gitea-dev
docker volume rm gitea-data
```

## Test GitHub Import

1. In Gitea UI, click "+" → "New Migration"
2. Select "GitHub"
3. Clone Address: `https://github.com/octocat/Hello-World`
4. (Optional) GitHub Token for private repos
5. Click "Migrate Repository"

This tests the import feature you'll use in SciTeX Cloud!

## Next Steps

Now that Gitea is running:
1. ✅ Complete initial setup (this doc)
2. ⏳ Explore Gitea features
3. ⏳ Test API with curl
4. ⏳ Build Django integration

## Quick Reference

| What | Value |
|------|-------|
| **Web UI** | http://localhost:3000 |
| **SSH** | ssh://git@localhost:2222 |
| **HTTP Clone** | http://localhost:3000/username/repo.git |
| **SSH Clone** | git@localhost:2222/username/repo.git |
| **Container Name** | scitex-gitea-dev |
| **Data Volume** | gitea-data |

## Troubleshooting

### Can't access localhost:3000
```bash
# Check if container is running
docker ps | grep gitea

# If not running, start it
docker start scitex-gitea-dev

# Check logs for errors
docker logs scitex-gitea-dev
```

### Port already in use
```bash
# Find what's using port 3000
lsof -i :3000

# Use different port (e.g., 3001)
docker rm scitex-gitea-dev
docker run -d --name scitex-gitea-dev -p 3001:3000 -p 2222:22 -v gitea-data:/data gitea/gitea:1.21
```

---

**You're ready to start building the Django integration!** 🚀

<!-- EOF -->