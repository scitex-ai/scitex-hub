# SciTeX Cloud: Institutional Deployment Architecture

**Created:** 2025-10-19
**Purpose:** Architecture design for multi-user institutional deployments

---

## Deployment Context

SciTeX Cloud is designed for institutional deployment where:
- **Multiple users** (10-500+ researchers) access the platform
- **User isolation** is required for security and resource management
- **Self-hosting** by universities, research institutes, or labs
- **HPC integration** may be needed for computational workloads
- **Data sovereignty** requires on-premise deployment

---

## Key Architectural Questions

### 1. **Where does computation happen?**

#### Option A: Centralized Web Server
```
[User Browser] → [Django Web Server] → [Gitea/PostgreSQL]
                        ↓
                  [Local Filesystem]
```
- **Use case:** Small institutions (<50 users), light compute
- **Container:** Docker (for web services)

#### Option B: Hybrid (Web + HPC)
```
[User Browser] → [Django Web Server] → [Gitea/PostgreSQL]
                        ↓
                  [HPC Job Scheduler]
                        ↓
                  [Singularity Containers on HPC]
```
- **Use case:** Research institutions with HPC clusters
- **Container:** Docker (web) + Singularity (compute)

#### Option C: Distributed
```
[User Browser] → [Personal SciTeX Instance (Singularity)]
                        ↓
                  [Shared Gitea Server]
```
- **Use case:** HPC-only environments, max user control
- **Container:** Singularity (unprivileged)

---

## Docker vs Singularity Decision Matrix

| Factor | Docker | Singularity | Recommendation |
|--------|--------|-------------|----------------|
| **Web services** (Django, Gitea, Nginx) | ✅ Excellent | ⚠️ Possible but awkward | Use Docker |
| **HPC compute jobs** | ❌ Requires root | ✅ Designed for HPC | Use Singularity |
| **Multi-tenancy** | ✅ Good isolation | ✅ User namespaces | Both work |
| **Networking** | ✅ Easy | ⚠️ More complex | Docker for web |
| **Shared filesystem** | ⚠️ Bind mounts | ✅ Native support | Singularity |
| **Job schedulers** (SLURM) | ❌ Incompatible | ✅ Designed for this | Singularity |
| **Security on shared systems** | ⚠️ Needs root daemon | ✅ Unprivileged | Singularity |
| **Ecosystem/tooling** | ✅ Huge | ⚠️ Smaller | Docker |

---

## Recommended Architecture: Hybrid Approach

### **Centralized Services (Docker)**
```yaml
# docker-compose.yml
services:
  django:
    image: scitex-cloud:latest
    ports: ["8000:8000"]
    volumes:
      - /shared/data:/data

  gitea:
    image: gitea/gitea:latest
    ports: ["3000:3000", "2222:22"]
    volumes:
      - gitea-data:/data

  postgres:
    image: postgres:15
    volumes:
      - postgres-data:/var/lib/postgresql/data
```

**Runs on:** Central web server (VM or bare metal)
**Serves:** Web UI, Git hosting, database

### **User Compute Jobs (Singularity)**
```bash
# User submits job via web UI
# Django generates SLURM script:

#!/bin/bash
#SBATCH --job-name=scitex-analysis
#SBATCH --mem=8G
#SBATCH --cpus-per-task=4

# Run analysis in Singularity container
singularity exec \
  --bind /shared/data/$USER:/data \
  /shared/containers/scitex-compute.sif \
  python /data/project/scripts/analysis.py
```

**Runs on:** HPC cluster nodes
**Serves:** Heavy computation, data processing

---

## User Isolation Strategies

### 1. **Django Multi-Tenancy**
```python
# apps/workspace_app/models.py
class Institution(models.Model):
    name = models.CharField(max_length=200)
    domain = models.CharField(max_length=200)  # e.g., "university.edu"
    storage_quota_gb = models.IntegerField(default=100)

class UserProfile(models.Model):
    user = models.OneToOneField(User)
    institution = models.ForeignKey(Institution)
    quota_used_gb = models.FloatField(default=0)

# Enforce quotas
def check_quota(user, size_bytes):
    profile = user.profile
    if profile.quota_used_gb + (size_bytes / 1e9) > profile.institution.storage_quota_gb:
        raise QuotaExceededError()
```

### 2. **Filesystem Isolation**
```
/shared/data/
├── institution1/
│   ├── user1/
│   │   ├── project1/
│   │   └── project2/
│   └── user2/
│       └── project1/
├── institution2/
│   └── user3/
│       └── project1/
```

**Permissions:**
```bash
# Each user directory: 700 (owner only)
chmod 700 /shared/data/institution1/user1
chown user1:user1 /shared/data/institution1/user1
```

### 3. **Gitea Organization Isolation**
```
Gitea Organizations:
├── university-lab1 (Organization)
│   ├── researcher1 (Member)
│   ├── researcher2 (Member)
│   └── project1 (Repository)
├── university-lab2 (Organization)
    ├── researcher3 (Member)
    └── project2 (Repository)
```

---

## Container Choice by Component

| Component | Container | Why |
|-----------|-----------|-----|
| **Django (Web)** | Docker | Better for web services, networking |
| **Gitea** | Docker | Web service, needs daemon |
| **PostgreSQL** | Docker | Standard deployment |
| **Nginx** | Docker | Web server |
| **Redis** | Docker | In-memory service |
| **Compute Jobs** | Singularity | HPC integration, no root needed |
| **Jupyter Notebooks** | Singularity | User-launched, HPC-friendly |
| **Data Processing** | Singularity | SLURM job submission |

---

## Deployment Scenarios

### Scenario 1: Small University Lab (10-50 users)

**Setup:**
- Single server (32GB RAM, 16 cores)
- Docker Compose for all services
- Local storage
- No HPC needed

```bash
# Install on single server
git clone https://github.com/scitex/scitex-cloud
cd scitex-cloud
docker-compose -f deployment/docker-compose.prod.yml up -d
```

**User workflow:**
- Web browser → Django UI
- Computations run on same server
- Good for: Light analysis, paper writing, literature search

---

### Scenario 2: Mid-Size Institute (50-200 users)

**Setup:**
- Web server: Docker services (Django, Gitea, PostgreSQL)
- HPC cluster: Singularity for compute
- Shared NFS/Lustre filesystem
- SLURM job scheduler

**Architecture:**
```
[Web Server (Docker)]
    ↓ (shared filesystem)
[HPC Cluster (SLURM + Singularity)]
```

**User workflow:**
1. Create project in web UI
2. Upload data / clone from GitHub
3. Submit compute job via UI
4. Django generates SLURM script
5. Job runs on HPC with Singularity
6. Results appear in web UI

**Good for:** Medium to heavy computation, multiple research groups

---

### Scenario 3: Large Research Center (200+ users)

**Setup:**
- Load-balanced Django (Kubernetes)
- Dedicated Gitea cluster
- PostgreSQL HA (replication)
- Multi-site HPC federation
- S3-compatible object storage

**Architecture:**
```
[Load Balancer]
    ↓
[Django Pods (Kubernetes)]
    ↓
[Gitea Cluster] + [PostgreSQL HA] + [Object Storage]
    ↓
[Multi-Site HPC (Singularity)]
```

**Good for:** Large-scale deployments, high availability requirements

---

## Practical Implementation: Hybrid Setup

### Step 1: Web Services (Docker)

**File:** `deployment/docker-compose.prod.yml`
```yaml
version: '3.8'

services:
  django:
    build: .
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000
    volumes:
      - /shared/scitex/data:/data
      - static:/static
    environment:
      - SCITEX_CLOUD_POSTGRES_URL=postgresql://scitex:password@postgres:5432/scitex
      - GITEA_URL=http://gitea:3000
    depends_on:
      - postgres
      - redis

  gitea:
    image: gitea/gitea:1.21
    volumes:
      - /shared/scitex/gitea:/data
    ports:
      - "3000:3000"
      - "2222:22"
    environment:
      - GITEA__database__DB_TYPE=postgres
      - GITEA__database__HOST=postgres:5432

  postgres:
    image: postgres:15
    volumes:
      - postgres-data:/var/lib/postgresql/data
    environment:
      - SCITEX_CLOUD_POSTGRES_DB=scitex
      - SCITEX_CLOUD_POSTGRES_USER=scitex
      - SCITEX_CLOUD_POSTGRES_PASSWORD=secure_password

  redis:
    image: redis:7-alpine

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - static:/static

volumes:
  postgres-data:
  static:
```

### Step 2: Compute Container (Singularity)

**File:** `deployment/singularity/scitex-compute.def`
```singularity
Bootstrap: docker
From: python:3.11-slim

%labels
    Author SciTeX Cloud
    Version 1.0

%post
    # Install scientific Python stack
    pip install --no-cache-dir \
        numpy pandas scipy matplotlib seaborn \
        scikit-learn jupyter notebook \
        torch torchvision \
        tensorflow

    # Install SciTeX tools
    pip install scitex-scholar scitex-code scitex-viz scitex-writer

%environment
    export LC_ALL=C
    export PATH=/opt/conda/bin:$PATH

%runscript
    exec python "$@"
```

**Build:**
```bash
sudo singularity build scitex-compute.sif scitex-compute.def
```

### Step 3: Job Submission from Django

**File:** `apps/compute_app/job_manager.py`
```python
import subprocess
from pathlib import Path

class SLURMJobManager:
    """Submit compute jobs to HPC via SLURM"""

    def submit_analysis_job(self, user, project, script_path):
        """Submit Python script as SLURM job"""

        # Generate SLURM script
        slurm_script = f"""#!/bin/bash
#SBATCH --job-name=scitex-{project.slug}
#SBATCH --output=/shared/scitex/logs/{user.username}-%j.out
#SBATCH --error=/shared/scitex/logs/{user.username}-%j.err
#SBATCH --mem=8G
#SBATCH --cpus-per-task=4
#SBATCH --time=04:00:00

# Run in Singularity container
singularity exec \\
  --bind /shared/scitex/data/{user.username}:/data \\
  /shared/containers/scitex-compute.sif \\
  python /data/{project.slug}/{script_path}
"""

        # Write script
        script_file = Path(f"/tmp/scitex-job-{project.id}.sh")
        script_file.write_text(slurm_script)

        # Submit job
        result = subprocess.run(
            ['sbatch', str(script_file)],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            # Parse job ID from output
            job_id = result.stdout.split()[-1]
            return {'success': True, 'job_id': job_id}
        else:
            return {'success': False, 'error': result.stderr}
```

---

## Security Considerations

### 1. **User Isolation**
```python
# Prevent path traversal
def sanitize_path(user, project, file_path):
    base_path = Path(f"/shared/scitex/data/{user.username}/{project.slug}")
    full_path = (base_path / file_path).resolve()

    if not str(full_path).startswith(str(base_path)):
        raise SecurityError("Path traversal attempt")

    return full_path
```

### 2. **Resource Quotas**
```python
# Enforce storage quotas
@receiver(post_save, sender=Project)
def check_storage_quota(sender, instance, **kwargs):
    user = instance.owner
    total_usage = Project.objects.filter(owner=user).aggregate(
        total=Sum('storage_used')
    )['total'] or 0

    if total_usage > user.profile.storage_quota_bytes:
        raise QuotaExceededError()
```

### 3. **SLURM Job Limits**
```bash
# /etc/slurm/slurm.conf
# Per-user limits
MaxJobs=10
MaxSubmit=20
DefMemPerCPU=2048
MaxMemPerNode=64000
```

---

## Migration Path

### Phase 1: Development (Week 1-2)
- ✅ Use direct Gitea binary (no containers)
- ✅ SQLite for database
- ✅ Local filesystem
- **Goal:** Build features, test integration

### Phase 2: Single-Server Deployment (Week 3-4)
- ✅ Docker Compose for web services
- ✅ PostgreSQL for production
- ✅ Nginx reverse proxy
- **Goal:** Functional institutional deployment

### Phase 3: HPC Integration (Week 5-8)
- ✅ Add Singularity support
- ✅ SLURM job submission
- ✅ Shared filesystem integration
- **Goal:** Scale to HPC workloads

---

## Decision Guide

**Start with Docker if:**
- ✅ You have a dedicated server/VM
- ✅ Users access via web only
- ✅ No HPC cluster
- ✅ <50 users

**Add Singularity when:**
- ✅ You have HPC cluster
- ✅ Users need heavy computation
- ✅ SLURM/PBS job scheduler
- ✅ Shared filesystem (NFS/Lustre)

**Use BOTH for:**
- ✅ Institutional deployment with HPC
- ✅ Web UI + compute separation
- ✅ Best of both worlds

---

## Next Steps

1. **For Development:** Start with direct Gitea binary (no containers)
2. **For Production:** Prepare Docker Compose setup
3. **For HPC:** Build Singularity compute container
4. **Document:** Write admin guide for IT departments

---

## Conclusion

**Recommendation:**
- **Development:** Direct binary (no containers)
- **Web Services:** Docker
- **HPC Compute:** Singularity
- **Institutional Deployment:** Hybrid (both)

This gives you flexibility to deploy in various institutional environments while keeping development simple.
