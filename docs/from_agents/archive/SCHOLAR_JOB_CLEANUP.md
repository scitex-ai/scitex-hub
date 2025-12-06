# SciTeX Scholar - Automatic Job Cleanup

## Overview

The BibTeX enrichment system has built-in protection against malicious attacks and resource exhaustion through **automatic stale job cleanup**.

## Multi-Layered Defense

### Layer 1: Inline Cleanup (On Upload)
When users upload a new BibTeX file, the system automatically checks for and fails any stale jobs:
- Processing jobs stuck for >10 minutes
- Pending jobs stuck for >5 minutes

**Location:** `apps/scholar_app/bibtex_views.py::bibtex_upload()`

### Layer 2: Periodic Cleanup (Every 5 Minutes)
A systemd timer runs automatic cleanup to prevent:
- Resource exhaustion attacks
- Database bloat from abandoned jobs
- Malicious job spam

**Setup:**
```bash
# Install and enable the timer
cd /home/ywatanabe/proj/scitex-cloud
./deployment/scripts/setup_cleanup_timer.sh
```

### Layer 3: Manual Cleanup (On Demand)
Run cleanup manually when needed:

```bash
# Dry run - see what would be done
python manage.py cleanup_stale_jobs --dry-run

# Clean up stale jobs
python manage.py cleanup_stale_jobs

# Clean up stale jobs + delete old jobs (>30 days)
python manage.py cleanup_stale_jobs --delete-old-jobs

# Custom retention period
python manage.py cleanup_stale_jobs --delete-old-jobs --retention-days=7
```

## Cleanup Rules

### Stale Job Detection
1. **Processing jobs**: Failed if running >10 minutes
2. **Pending jobs**: Failed if waiting >5 minutes
3. **Old jobs**: Deleted if completed/failed >30 days ago (optional)

### Why These Timeouts?
- **10 min processing**: Most enrichment jobs complete in 2-5 minutes. 10 minutes is generous.
- **5 min pending**: Jobs should start within seconds. 5 minutes means something is wrong.
- **30 day retention**: Keeps recent history for debugging while preventing bloat.

## Security Benefits

### Attack Prevention
- **Resource exhaustion**: Automatic cleanup prevents accumulation of stuck jobs
- **Database bloat**: Old jobs are deleted to maintain performance
- **Denial of service**: One-job-per-user limit + automatic cleanup prevents abuse

### Normal Operation
- Users get immediate feedback if jobs timeout
- Stale jobs don't block new uploads
- System self-heals from errors

## Monitoring

### Check Timer Status
```bash
# Is the timer running?
systemctl --user status scitex-cleanup-jobs.timer

# When will it run next?
systemctl --user list-timers scitex-cleanup-jobs.timer

# View recent cleanup logs
journalctl --user -u scitex-cleanup-jobs -n 50
```

### Check Job Statistics
```bash
# See current system status
python manage.py cleanup_stale_jobs --dry-run
```

Output shows:
- Total jobs in system
- Active jobs (currently running)
- Completed jobs
- Failed jobs

## Timer Management

### Enable/Disable
```bash
# Enable timer (starts automatically on boot)
systemctl --user enable scitex-cleanup-jobs.timer

# Disable timer
systemctl --user disable scitex-cleanup-jobs.timer

# Stop timer (until next boot)
systemctl --user stop scitex-cleanup-jobs.timer

# Start timer
systemctl --user start scitex-cleanup-jobs.timer
```

### Modify Schedule
Edit `/home/ywatanabe/.config/systemd/user/scitex-cleanup-jobs.timer`:

```ini
[Timer]
# Run every 5 minutes (current)
OnUnitActiveSec=5min

# Or run every hour
OnUnitActiveSec=1h

# Or run every 30 seconds (aggressive)
OnUnitActiveSec=30s
```

Then reload:
```bash
systemctl --user daemon-reload
systemctl --user restart scitex-cleanup-jobs.timer
```

## Troubleshooting

### Jobs Still Stuck After Cleanup?
1. Check if timer is running: `systemctl --user status scitex-cleanup-jobs.timer`
2. Run manual cleanup: `python manage.py cleanup_stale_jobs`
3. Check logs: `journalctl --user -u scitex-cleanup-jobs -n 50`

### Timer Not Running?
```bash
# Enable lingering (allows user services to run without login)
loginctl enable-linger $USER

# Restart timer
systemctl --user restart scitex-cleanup-jobs.timer
```

### Too Many Failed Jobs?
This might indicate:
- Timeout too aggressive (increase from 10 min?)
- System resource issues (CPU/memory)
- Network connectivity problems
- Bug in enrichment pipeline

Check logs: `journalctl --user -u scitex-cleanup-jobs`

## Production Recommendations

### For High Traffic Sites
1. **Run cleanup more frequently** (every 1-2 minutes instead of 5)
2. **Enable automatic deletion** of old jobs
3. **Monitor job queue depth** via metrics
4. **Set up alerts** for excessive failed jobs

### For Low Traffic Sites
1. **Keep 5-minute interval** (sufficient)
2. **Manual deletion** of old jobs when needed
3. **Monitor weekly** via dry-run command

## Implementation Details

### Files
- `apps/scholar_app/models.py::is_stale()` - Detection logic
- `apps/scholar_app/bibtex_views.py::bibtex_upload()` - Inline cleanup
- `apps/scholar_app/management/commands/cleanup_stale_jobs.py` - Cleanup command
- `deployment/systemd/scitex-cleanup-jobs.service` - Systemd service
- `deployment/systemd/scitex-cleanup-jobs.timer` - Systemd timer
- `deployment/scripts/setup_cleanup_timer.sh` - Installation script

### Testing
```bash
# Test dry run
python manage.py cleanup_stale_jobs --dry-run

# Test actual cleanup
python manage.py cleanup_stale_jobs

# Test with deletion
python manage.py cleanup_stale_jobs --delete-old-jobs --retention-days=0
```

## Summary

✅ **Multi-layered defense** prevents malicious attacks
✅ **Automatic recovery** from stuck/stale jobs
✅ **No partial results** - only complete enrichments provided
✅ **Self-healing system** - minimal manual intervention needed
✅ **Security hardened** - resource exhaustion prevention built-in
