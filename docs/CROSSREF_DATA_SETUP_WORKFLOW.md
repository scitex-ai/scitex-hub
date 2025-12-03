# CrossRef Local Data Setup - Complete Workflow

**Author**: Claude Code
**Date**: 2025-12-03
**Reality Check**: Data download and indexing will take DAYS, not hours

## Current Status - What You Already Have

Based on your NAS directory structure:

```
/home/ywatanabe/crossref_local/
├── data/                    # ← YOUR DATA IS HERE
├── dois2sqlite/             # ← Tool to convert DOIs to SQLite
├── impact_factor/           # ← Impact factor calculations
├── labs-data-file-api/      # ← CrossRef Labs Data File API
└── README.md
```

**IMPORTANT**: You likely already have the database! Let's check before re-downloading.

## Phase 0: Assess What You Have (DO THIS FIRST)

### Check Existing Data

```bash
# 1. Check if database exists and its size
ls -lh /mnt/nas_ug/crossref_local/data/

# 2. If database exists, check its contents
sqlite3 /mnt/nas_ug/crossref_local/data/crossref.db << EOF
.tables
SELECT COUNT(*) as total_papers FROM works;
SELECT MIN(year), MAX(year) FROM works WHERE year IS NOT NULL;
.schema works
.indices works
EOF

# 3. Check database size and last modified
du -sh /mnt/nas_ug/crossref_local/data/
stat /mnt/nas_ug/crossref_local/data/crossref.db
```

### Assess Current State

| Scenario | Action |
|----------|--------|
| **Database exists + has data + has indices** | ✅ **USE IT!** Just build Docker API |
| **Database exists + has data + NO indices** | Add indices (hours, not days) |
| **Database exists + empty** | Need to download (days) |
| **No database** | Full setup needed (days) |

## Complete Workflow - From Scratch

**Timeline**: 3-7 days depending on data size and network speed

### Step 1: Understand CrossRef Data Sources (1 hour)

CrossRef provides data through:

1. **Public API** (slow, rate-limited)
   - 50 requests/second (polite pool)
   - ~140M works total
   - **NOT RECOMMENDED** for bulk download

2. **Plus API** (faster, requires authorization)
   - For Plus subscribers
   - Metadata snapshots available

3. **Public Data File** (BEST for bulk)
   - Monthly snapshots
   - ~400GB compressed, ~2TB uncompressed
   - Available via academic torrents or direct download
   - URL: https://www.crossref.org/blog/2022-public-data-file-now-available-with-new-and-improved-retrieval-options/

### Step 2: Choose Your Approach

#### Option A: Full Database (Recommended for Production)

**Download CrossRef Public Data File**

```bash
# Time: 1-3 days depending on network
# Size: ~400GB compressed → ~2TB uncompressed

# 1. Download from CrossRef
# https://www.crossref.org/blog/2022-public-data-file-now-available-with-new-and-improved-retrieval-options/

cd /mnt/nas_ug/crossref_local/data/

# Download via torrent (recommended) or wget
# Academic Torrents: https://academictorrents.com/
wget https://crossref-data.s3.amazonaws.com/public-data-file/crossref-2024.tar.gz

# 2. Extract
tar -xzvf crossref-2024.tar.gz
```

#### Option B: Subset Database (Faster for Development)

**Use CrossRef API + dois2sqlite**

```bash
# Time: Hours to days depending on subset size
# Size: Depends on subset

cd /mnt/nas_ug/crossref_local/

# Clone or use existing dois2sqlite
cd dois2sqlite/

# Configure for subset (e.g., specific year, field, journal)
python download_subset.py \
    --year-start 2020 \
    --year-end 2024 \
    --fields "computer science,neuroscience" \
    --output ../data/crossref_subset.db
```

#### Option C: Sample Database (Fastest for Development)

**Use existing sample or create small test DB**

```bash
# Time: Minutes
# Size: MB to GB

# Create sample with top journals
python create_sample_db.py \
    --journals "Nature,Science,Cell,PLOS ONE" \
    --papers-per-journal 1000 \
    --output ../data/crossref_sample.db
```

### Step 3: Convert to SQLite (1-2 days)

CrossRef data comes as JSON lines. Convert to SQLite:

```bash
cd /mnt/nas_ug/crossref_local/dois2sqlite/

# Process JSON to SQLite
# This will take 1-2 days for full dataset
python json_to_sqlite.py \
    --input ../data/crossref-2024/*.json.gz \
    --output ../data/crossref.db \
    --batch-size 10000 \
    --workers 8

# Monitor progress
tail -f logs/conversion.log
```

**Schema Created**:
```sql
CREATE TABLE works (
    doi TEXT PRIMARY KEY,
    title TEXT,
    authors TEXT,  -- JSON array
    year INTEGER,
    journal TEXT,
    issn TEXT,
    publisher TEXT,
    abstract TEXT,
    citation_count INTEGER,
    references TEXT,  -- JSON array of DOIs
    metadata TEXT  -- Full JSON
);

CREATE TABLE references (
    citing_doi TEXT,
    cited_doi TEXT,
    PRIMARY KEY (citing_doi, cited_doi)
);

CREATE TABLE journals (
    issn TEXT PRIMARY KEY,
    name TEXT,
    publisher TEXT,
    total_papers INTEGER
);
```

### Step 4: Add Indices (4-8 hours for full DB)

**CRITICAL FOR PERFORMANCE**

```bash
cd /mnt/nas_ug/crossref_local/

# Run index creation script
python add_indices.py --database data/crossref.db
```

```sql
-- indices.sql
-- This will take 4-8 hours for full database

-- Primary lookups
CREATE INDEX IF NOT EXISTS idx_doi ON works(doi);
CREATE INDEX IF NOT EXISTS idx_title ON works(title);
CREATE INDEX IF NOT EXISTS idx_year ON works(year);
CREATE INDEX IF NOT EXISTS idx_issn ON works(issn);

-- Full-text search (if supported)
CREATE VIRTUAL TABLE IF NOT EXISTS works_fts USING fts5(
    doi, title, authors, abstract,
    content='works'
);

-- Citation graph
CREATE INDEX IF NOT EXISTS idx_citing_doi ON references(citing_doi);
CREATE INDEX IF NOT EXISTS idx_cited_doi ON references(cited_doi);

-- Journal lookups
CREATE INDEX IF NOT EXISTS idx_journal_issn ON journals(issn);
CREATE INDEX IF NOT EXISTS idx_journal_name ON journals(name);

-- Analyze for query optimization
ANALYZE;
```

**Progress Monitoring**:
```bash
# Check index creation progress
watch -n 60 'sqlite3 crossref.db "SELECT name FROM sqlite_master WHERE type=\"index\";"'
```

### Step 5: Validate Database (1 hour)

```bash
# Run validation tests
python validate_database.py --database data/crossref.db

# Check:
# - Row counts
# - Index coverage
# - Sample queries
# - Data integrity
```

## Optimized Workflow - Using What You Have

**IF YOU ALREADY HAVE DATA**, here's the smart approach:

### Quick Start (Hours, not Days)

```bash
# 1. Check what you have (5 minutes)
cd /mnt/nas_ug/crossref_local/
python check_database.py --database data/crossref.db > status.txt
cat status.txt

# 2. If data exists but no indices (4-8 hours)
python add_indices.py --database data/crossref.db

# 3. Build Docker API (30 minutes)
cd ~/proj/scitex-cloud/
make ENV=dev crossref-build
make ENV=dev crossref-up

# 4. Test it (5 minutes)
curl http://localhost:3333/health
curl "http://localhost:3333/api/search/?doi=10.1038/nature12345"

# DONE! Start using it immediately while optimizing in background
```

## Incremental Improvement Strategy

**Don't wait for perfection - start using it now!**

### Week 1: Minimum Viable Product
- ✅ Use existing database (even if incomplete)
- ✅ Add basic indices (DOI, title)
- ✅ Build Docker API
- ✅ Integrate with Django
- ⏳ Download updates in background

### Week 2: Enhance Coverage
- ✅ Add full-text search indices
- ✅ Import recent papers (2023-2024)
- ✅ Add citation data
- ⏳ Continue downloading historical data

### Week 3: Optimize Performance
- ✅ Add advanced indices
- ✅ Implement caching layers
- ✅ Benchmark and tune queries
- ✅ Add monitoring

### Month 2: Complete Database
- ✅ Full historical data imported
- ✅ All indices optimized
- ✅ Citation graph complete
- ✅ Production-ready

## Realistic Timeline

| Task | Time (Full DB) | Time (Subset) | Time (Sample) |
|------|----------------|---------------|---------------|
| **Download data** | 1-3 days | 4-24 hours | 5 minutes |
| **Convert to SQLite** | 1-2 days | 2-12 hours | 5 minutes |
| **Add indices** | 4-8 hours | 1-4 hours | 5 minutes |
| **Validate** | 1 hour | 30 minutes | 5 minutes |
| **Build Docker API** | 30 minutes | 30 minutes | 30 minutes |
| **Test & Deploy** | 1 hour | 1 hour | 1 hour |
| **TOTAL** | **3-7 days** | **1-2 days** | **1 hour** |

## Recommended Approach

### For Development (NOW)
```bash
# Use sample database to start development
# Build API, test integration, develop features
# Timeline: 1-2 hours

cd /mnt/nas_ug/crossref_local/
python create_sample_db.py \
    --size small \
    --output data/crossref_sample.db

# Point Docker to sample DB
export CROSSREF_DB_PATH=/data/crossref_sample.db
make ENV=dev crossref-up
```

### For Production (PARALLEL)
```bash
# Download full database in parallel
# Don't wait for this to finish development
# Timeline: 3-7 days (background process)

cd /mnt/nas_ug/crossref_local/
nohup python download_and_convert.py \
    --full \
    --output data/crossref_full.db \
    > logs/download.log 2>&1 &

# Monitor progress
tail -f logs/download.log

# When ready, swap databases
docker-compose stop crossref-local
# Update docker-compose.yml to use crossref_full.db
docker-compose up -d crossref-local
```

## Database Maintenance

### Monthly Updates

```bash
# Download new records (monthly)
cd /mnt/nas_ug/crossref_local/
python update_database.py \
    --database data/crossref.db \
    --since "2024-11-01"

# Rebuild indices if needed
sqlite3 data/crossref.db "REINDEX;"
sqlite3 data/crossref.db "ANALYZE;"
```

### Backup Strategy

```bash
# Backup before major updates
cp data/crossref.db data/crossref_backup_$(date +%Y%m%d).db

# Or incremental backup
sqlite3 data/crossref.db ".backup data/crossref_backup.db"
```

## Tools You Need

### 1. Download Script

```python
# scripts/download_crossref.py

import requests
import gzip
import json
from pathlib import Path
from tqdm import tqdm

def download_crossref_data(output_dir: Path, year_start: int, year_end: int):
    """Download CrossRef data for specified years"""
    # Implementation using CrossRef API or data files
    pass
```

### 2. Conversion Script

```python
# scripts/json_to_sqlite.py

import sqlite3
import json
import gzip
from multiprocessing import Pool

def convert_json_to_sqlite(json_files: list, db_path: Path, workers: int = 8):
    """Convert JSON files to SQLite database"""
    # Parallel processing for speed
    pass
```

### 3. Index Script

```python
# scripts/add_indices.py

import sqlite3
import time

def add_indices(db_path: Path):
    """Add all necessary indices"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    indices = [
        "CREATE INDEX IF NOT EXISTS idx_doi ON works(doi)",
        "CREATE INDEX IF NOT EXISTS idx_title ON works(title)",
        # ... more indices
    ]

    for idx_sql in indices:
        print(f"Creating index: {idx_sql}")
        start = time.time()
        cursor.execute(idx_sql)
        elapsed = time.time() - start
        print(f"  Done in {elapsed:.2f} seconds")

    cursor.execute("ANALYZE")
    conn.commit()
    conn.close()
```

## FAQ

**Q: Can I use the API while downloading data?**
A: YES! Use a sample database for development, swap to full database when ready.

**Q: How much disk space needed?**
A: Full database: ~2TB uncompressed, ~400GB compressed
   Subset (2020-2024): ~200-400GB
   Sample: ~1-10GB

**Q: Can I skip citation data?**
A: Yes, start with basic metadata, add citations later.

**Q: Do I need to re-download periodically?**
A: Monthly updates recommended, but not required for static research.

**Q: What if download fails halfway?**
A: Use incremental downloads, checkpoint progress, resume from last point.

---

## ACTION PLAN

**TODAY** (if you don't remember the workflow):

```bash
# 1. Check what you already have
ssh ywatanabe@nas
cd /home/ywatanabe/crossref_local/
ls -lh data/
cat README.md  # Your past self may have documented it!

# 2. If database exists:
sqlite3 data/crossref.db ".tables"
sqlite3 data/crossref.db "SELECT COUNT(*) FROM works;"

# 3. Report back what you find!
```

**THEN** we'll decide:
- Use existing database + add indices (hours)
- Download subset (1-2 days)
- Download full dataset (3-7 days)

**DON'T START FROM SCRATCH** if you already have data!
