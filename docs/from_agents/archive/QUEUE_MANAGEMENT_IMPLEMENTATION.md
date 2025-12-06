# BibTeX Enrichment Queue Management System

## Overview

The SciTeX Scholar BibTeX enrichment system includes a comprehensive queue management implementation that ensures fair resource allocation, user privacy, and efficient processing.

## Features

### 1. One Job Per User Constraint

**Implementation:** `apps/scholar_app/bibtex_views.py:87-109`

- Each user (authenticated or visitor) can only have ONE active or pending job at a time
- When attempting to upload a new file with an active job, the system returns:
  - HTTP 429 (Too Many Requests) for AJAX requests
  - Error message showing the existing job filename
  - Job ID for redirection to existing job status

**Code Example:**
```python
existing_active_job = BibTeXEnrichmentJob.objects.filter(
    user=request.user,
    status__in=['pending', 'processing']
).first()

if existing_active_job:
    return JsonResponse({
        'success': False,
        'error': f'You already have a job in progress: "{existing_active_job.original_filename}"',
        'existing_job_id': str(existing_active_job.id),
    }, status=429)
```

### 2. Queue Position Tracking

**Implementation:** `apps/scholar_app/bibtex_views.py:578-600`

- Jobs are ordered by `created_at` timestamp (FIFO - First In, First Out)
- Each user sees their position in the global queue
- Position is calculated dynamically based on pending jobs

**API Response:**
```json
{
  "jobs": {
    "queued": [{
      "id": "uuid",
      "user": "You",
      "filename": "references.bib",
      "position": 3,
      "can_cancel": true
    }],
    "user_queue_position": 3
  }
}
```

### 3. Privacy & Security

**Implementation:** `apps/scholar_app/bibtex_views.py:556-600`

**Security Measures:**
- Users ONLY see details of their own jobs
- Other users' jobs are hidden completely
- Aggregate counts shown for total system load
- No usernames, filenames, or job IDs exposed across users

**What Users See:**
- ✅ Their own job details (filename, progress, position)
- ✅ Total count of active/queued jobs in system
- ❌ Other users' filenames
- ❌ Other users' usernames
- ❌ Other users' progress or job IDs

**Example:**
```python
# Only show owner's jobs
if is_owner:
    active_jobs_list.append({
        'id': str(job.id),
        'user': 'You',
        'filename': job.original_filename,
        'can_cancel': True,
    })
# Don't add other users' jobs to the list
```

### 4. Visual Queue Indicators

**Implementation:** `apps/scholar_app/templates/scholar_app/index.html:2678-2715`

**Color-coded Positions:**
- **Position #1** - Green border, "⭐ Next up" badge
- **Position #2** - Blue border, "↑ 2nd in line" badge
- **Position #3+** - Orange border, "⏳ Position #N" badge

**Additional Info:**
- For positions > 3: Shows "(N-1 jobs ahead)"
- Each queued job has a cancel button (if owner)
- Real-time updates via AJAX polling

**Visual Examples:**
```
┌─────────────────────────────────────────┐
│ [GREEN] ⭐ Next up                      │
│ 📄 my_references.bib              [×]   │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ [BLUE] ↑ 2nd in line                   │
│ 📄 literature_review.bib          [×]   │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ [ORANGE] ⏳ Position #5                 │
│ 📄 citations.bib (4 jobs ahead)   [×]   │
└─────────────────────────────────────────┘
```

### 5. Resource Monitoring

**Implementation:** `apps/scholar_app/bibtex_views.py:520-617`

**Monitored Metrics:**
- CPU usage (%)
- Memory usage (%)
- Available memory (GB)
- Active jobs count
- Queued jobs count
- Completed jobs (last hour)

**API Endpoint:** `/scholar/api/bibtex/resource-status/`

**Response:**
```json
{
  "system": {
    "cpu_percent": 45.2,
    "memory_percent": 68.5,
    "memory_available_gb": 8.42
  },
  "jobs": {
    "active_count": 2,
    "queued_count": 5,
    "completed_last_hour": 12,
    "active": [...],
    "queued": [...]
  },
  "timestamp": "2025-10-22T12:34:56Z"
}
```

### 6. Job Cancellation

**Implementation:** `apps/scholar_app/bibtex_views.py:620-641`

**Features:**
- Users can cancel their own pending or processing jobs
- Cancelled jobs marked as 'failed' with error message "Cancelled by user"
- Cannot cancel completed or already failed jobs
- Confirmation dialog in UI

**API Endpoint:** `/scholar/api/bibtex/job/<job_id>/cancel/`

**Security:**
- Authenticated users: verified by `user` field
- Visitor users: verified by `session_key` field

### 7. Visitor User Support

**Implementation:** Throughout `bibtex_views.py`

- Visitor users tracked by Django session key
- Same queue rules apply (one job per session)
- Jobs isolated by session key
- Prompt to sign up to save results

## Architecture

### Database Model

**Model:** `apps/scholar_app/models.py:1313-1413`

```python
class BibTeXEnrichmentJob(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, ...)  # Null for visitor
    session_key = models.CharField(...)   # For visitor users
    status = models.CharField(...)
    # ... other fields
```

**Indexes:**
```python
indexes = [
    models.Index(fields=['user', '-created_at']),
    models.Index(fields=['session_key', '-created_at']),
    models.Index(fields=['status']),
]
```

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/scholar/api/bibtex/upload/` | POST | Upload and queue job |
| `/scholar/api/bibtex/job/<id>/status/` | GET | Get job progress |
| `/scholar/api/bibtex/job/<id>/cancel/` | POST | Cancel job |
| `/scholar/api/bibtex/resource-status/` | GET | Get queue status |

### Frontend Updates

**Polling Interval:** 2 seconds (when upload form is visible)

**Update Flow:**
1. Page loads → Start polling `resource-status`
2. Every 2s → Fetch latest queue/resource data
3. Update UI → Show user's jobs + system counts
4. On job completion → Refresh, show download button

## Usage Examples

### Example 1: User Uploads File

```
User uploads "references.bib"
  ↓
Check for existing active job
  ↓
No existing job → Create new job (status: pending)
  ↓
Start processing in background thread
  ↓
Job status: pending → processing
  ↓
UI shows progress bar, cancel button
  ↓
Job completes → status: completed
  ↓
UI shows download button
```

### Example 2: User Has Active Job

```
User uploads "citations.bib"
  ↓
Check for existing active job
  ↓
Found: "references.bib" (processing)
  ↓
Return error: "You already have a job in progress"
  ↓
UI shows error + link to existing job
```

### Example 3: Multiple Users

```
System State:
- User A: 1 active job
- User B: 1 queued job (position #1)
- User C: 1 queued job (position #2)

User A sees:
  Active: My job (75% complete)
  Queued: 2 job(s) in system queue

User B sees:
  Active: 1 job(s) currently processing
  Queued: ⭐ Next up - my_file.bib

User C sees:
  Active: 1 job(s) currently processing
  Queued: ↑ 2nd in line - other_file.bib
```

## Future Enhancements

### Planned Features

1. **Smart Queue Management**
   - Priority based on file size
   - Time-based limits (e.g., max 30 min per job)
   - Automatic queue cleanup

2. **Better Resource Allocation**
   - Dynamic worker count based on system load
   - Pause/resume jobs
   - Job scheduling (off-peak processing)

3. **Enhanced Notifications**
   - Email when job completes
   - Browser notifications (Web Push API)
   - Slack/Discord webhooks

4. **Queue Analytics**
   - Average wait time
   - Processing time statistics
   - Peak usage hours

## Testing

### Manual Testing Checklist

- [ ] Upload file as authenticated user
- [ ] Upload file as visitor user
- [ ] Try to upload second file with active job (should fail)
- [ ] Cancel pending job
- [ ] Cancel processing job
- [ ] Check queue position updates
- [ ] Verify privacy (open in incognito, shouldn't see other jobs)
- [ ] Check resource stats update every 2s
- [ ] Complete a job and download results

### Automated Tests (TODO)

```python
def test_one_job_per_user():
    # Create user and first job
    # Try to create second job → should fail
    pass

def test_queue_position():
    # Create 3 jobs for 3 users
    # Check positions: 1, 2, 3
    pass

def test_privacy():
    # User A creates job
    # User B shouldn't see User A's job details
    pass
```

## Troubleshooting

### Issue: Jobs stuck in "pending"

**Cause:** Background thread failed to start
**Solution:** Check server logs, restart Django

### Issue: Queue position not updating

**Cause:** AJAX polling stopped
**Solution:** Check browser console, refresh page

### Issue: Can't cancel job

**Cause:** Job already completed/failed
**Solution:** Refresh page to see latest status

## Related Files

- Models: `apps/scholar_app/models.py` (lines 1313-1413)
- Views: `apps/scholar_app/bibtex_views.py`
- Templates: `apps/scholar_app/templates/scholar_app/index.html`
- URLs: `apps/scholar_app/urls.py`
- TODO: `TODOS/10_SCITEX_SCHOLAR.md`

---

**Last Updated:** 2025-10-22
**Author:** Claude Code
**Version:** 1.0
