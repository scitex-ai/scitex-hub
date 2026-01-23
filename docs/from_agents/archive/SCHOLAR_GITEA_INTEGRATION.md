<!-- ---
!-- Timestamp: 2025-10-20 21:00:00
!-- Author: ywatanabe (with Claude Code)
!-- File: /home/ywatanabe/proj/scitex-cloud/docs/SCHOLAR_GITEA_INTEGRATION.md
!-- Status: IMPLEMENTED
!-- --- -->

# Scholar-Gitea Integration

**Status:** ✅ Implemented and Working
**Date:** 2025-10-20
**Version:** 1.0

---

## Overview

The Scholar module integrates with Gitea to automatically version control enriched bibliography files. When users enrich their BibTeX files with abstracts, citation counts, and metadata, the results are automatically committed to their project's Gitea repository.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        USER WORKFLOW                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Upload .bib file                                         │
│  2. Select project from dropdown                             │
│  3. Scholar enriches bibliography                            │
│  4. Auto-commit to Gitea                                     │
│  5. Enhanced .bib ready for Writer module                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    SCHOLAR ENRICHMENT                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ScholarPipelineBibTeX                                       │
│  ├── Extract paper metadata from .bib                        │
│  ├── Query Semantic Scholar API for abstracts               │
│  ├── Query CrossRef for citation counts                     │
│  ├── Download PDFs where available                          │
│  └── Generate enriched .bib file                            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     GITEA INTEGRATION                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Copy enriched .bib to /data/username/project/references/│
│  2. git add references/references.bib                        │
│  3. git commit -m "Scholar: Enriched bibliography (X/Y)"    │
│  4. git push origin develop                                 │
│  5. Update enrichment_summary with commit status            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     GITEA REPOSITORY                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  username/project-name/                                      │
│  ├── references/                                             │
│  │   └── references.bib  ← Enriched bibliography            │
│  ├── paper/                                                  │
│  └── .git/                                                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Features

### 1. Automatic Bibliography Enrichment

**What Gets Enriched:**
- ✅ **Abstracts**: Full paper abstracts from Semantic Scholar
- ✅ **Citation Counts**: From CrossRef, Semantic Scholar, Google Scholar
- ✅ **Journal Metrics**: Impact factors, rankings
- ✅ **PDF Downloads**: Automatic acquisition from open sources
- ✅ **Metadata**: Keywords, authors, affiliations, DOIs

### 2. Project Integration

**BibTeX Enrichment Form:**
- **Project Selector**: Dropdown of user's projects
- **Gitea Auto-Commit**: When project selected, enriched .bib auto-committed
- **Manual Download**: When no project selected, user downloads manually

**UI Elements:**
```html
<!-- Project Selection -->
<select name="project_id">
  <option value="">-- No Project (Manual Download Only) --</option>
  <option value="{{ project.id }}">{{ project.name }}</option>
</select>

<!-- Help Text -->
<small>
  Enriched .bib will be auto-committed to project's Gitea repository
  at /references/references.bib
</small>
```

### 3. Gitea Version Control

**Auto-Commit Workflow:**
1. Enrichment job completes successfully
2. Check if project has `git_clone_path`
3. Create `/references/` directory if needed
4. Copy enriched .bib to `references/references.bib`
5. Use `git_operations.py::auto_commit_file()`
6. Record commit status in `enrichment_summary`

**Commit Message Format:**
```
Scholar: Enriched bibliography (15/20 papers enriched)
```

### 4. Status Tracking

**enrichment_summary JSON Field:**
```json
{
  "gitea_commit": true,
  "gitea_message": "Scholar: Enriched bibliography (15/20 papers enriched)",
  "gitea_error": null
}
```

**UI Display:**
- ✅ Green success card: "Enriched bibliography successfully committed"
- ⚠ Yellow warning card: "Auto-commit failed, download manually"
- 🔗 Direct link to Gitea repository

---

## Implementation Details

### Models

**BibTeXEnrichmentJob** (`apps/scholar_app/models.py:1313-1399`):
```python
class BibTeXEnrichmentJob(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    project = models.ForeignKey(
        'project_app.Project',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Associated project for Gitea integration"
    )
    input_file = models.FileField(upload_to='bibtex_uploads/%Y/%m/%d/')
    output_file = models.FileField(upload_to='bibtex_enriched/%Y/%m/%d/')

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    enrichment_summary = models.JSONField(
        default=dict,
        blank=True,
        help_text="Gitea commit status, citation counts, etc."
    )
```

### Views

**bibtex_upload** (`apps/scholar_app/bibtex_views.py:51-103`):
```python
def bibtex_upload(request):
    """Handle BibTeX upload and create enrichment job."""

    # Get project if specified
    project_id = request.POST.get('project_id')
    project = Project.objects.get(id=project_id) if project_id else None

    # Create enrichment job
    job = BibTeXEnrichmentJob.objects.create(
        user=request.user,
        project=project,  # Link to project
        input_file=uploaded_file,
        num_workers=4,
        browser_mode='stealth',
    )

    return redirect('scholar_app:bibtex_job_detail', job_id=job.id)
```

**_process_bibtex_job** (`apps/scholar_app/bibtex_views.py:186-282`):
```python
def _process_bibtex_job(job):
    """Process BibTeX file and auto-commit to Gitea."""

    # Enrich bibliography
    papers = ScholarPipelineBibTeX.process_bibtex_file_async(...)

    # Gitea Integration
    if job.project and job.project.git_clone_path:
        # Copy enriched .bib to project repository
        project_bib_path = Path(job.project.git_clone_path) / 'references' / 'references.bib'
        shutil.copy(output_path, project_bib_path)

        # Auto-commit to Gitea
        commit_message = f"Scholar: Enriched bibliography ({job.processed_papers}/{job.total_papers} papers enriched)"
        success, output = auto_commit_file(
            project_dir=job.project.git_clone_path,
            filepath='references/references.bib',
            message=commit_message
        )

        # Track status
        job.enrichment_summary['gitea_commit'] = success
        job.enrichment_summary['gitea_message'] = commit_message

    job.save()
```

### Templates

**bibtex_enrichment.html** (Upload Form):
- Project selector dropdown
- Project label input (for non-project enrichment)
- Advanced options (workers, browser mode)
- Recent jobs table with Gitea status indicators

**bibtex_job_detail.html** (Job Status):
- Progress bar and job details
- Gitea integration status card
- Link to view in Gitea repository
- Download button for enriched .bib

---

## Usage

### For End Users

**1. Access Scholar Module:**
```
http://127.0.0.1:8000/scholar/bibtex/enrichment/
```

**2. Upload and Enrich:**
1. Select BibTeX file (.bib)
2. Choose project from dropdown (optional but recommended)
3. Click "Enrich BibTeX File"
4. Wait for processing (auto-refreshes every 5 seconds)
5. View enriched .bib committed to Gitea

**3. Access Enriched Bibliography:**
- **Via Gitea Web UI**: Click link in job detail page
- **Via Local Clone**: `/data/username/project/references/references.bib`
- **Manual Download**: Download button if no project selected

### For Developers

**Integrate with Other Modules:**

```python
# In Writer module - access enriched .bib
from apps.scholar_app.models import BibTeXEnrichmentJob

# Get latest enriched bibliography for project
job = BibTeXEnrichmentJob.objects.filter(
    project=project,
    status='completed',
    enrichment_summary__gitea_commit=True
).order_by('-completed_at').first()

if job:
    bib_path = Path(project.git_clone_path) / 'references' / 'references.bib'
    # Use enriched bibliography for manuscript compilation
```

---

## Benefits

### ✅ For Researchers

1. **Enriched Metadata**: Abstracts and citations improve AI-assisted writing
2. **Version Control**: Track changes to bibliography over time
3. **Collaboration**: Share enriched bibliographies via Gitea
4. **No Manual Work**: Automatic enrichment and commit

### ✅ For Writer Module

1. **Better AI Context**: Abstracts provide context for citation placement
2. **Citation Metrics**: Know which papers are highly cited
3. **PDF Access**: Download PDFs for reference
4. **Structured Data**: Clean BibTeX format ready for LaTeX

### ✅ For System Architecture

1. **Single Source of Truth**: Gitea stores enriched bibliographies
2. **Consistent Data**: All modules access same .bib from Gitea
3. **Audit Trail**: Git history tracks all bibliography changes
4. **Backup**: Gitea provides automatic backup

---

## Configuration

### Environment Variables

**Development** (`deployment/dotenvs/dotenv_dev`):
```bash
export SCITEX_CLOUD_GITEA_URL_DEV=http://localhost:3001
export SCITEX_CLOUD_GITEA_TOKEN_DEV=bfd4ecd8471bde7f3b7ee7e1ce3f86ec8c966a36
```

**Production** (`deployment/dotenvs/dotenv_prod`):
```bash
export SCITEX_CLOUD_GITEA_URL_PROD=https://git.scitex.ai
export SCITEX_CLOUD_GITEA_TOKEN_PROD=<production-token>
```

### Django Settings

**settings_dev.py**:
```python
GITEA_URL = os.environ.get('SCITEX_CLOUD_GITEA_URL_DEV', 'http://localhost:3001')
GITEA_TOKEN = os.environ.get('SCITEX_CLOUD_GITEA_TOKEN_DEV', '')
GITEA_INTEGRATION_ENABLED = True
```

---

## Database Schema

### Migration: 0003_add_project_to_bibtex_job.py

```python
operations = [
    migrations.AddField(
        model_name='bibtexenrichmentjob',
        name='project',
        field=models.ForeignKey(
            blank=True,
            help_text='Associated project for Gitea integration',
            null=True,
            on_delete=django.db.models.deletion.SET_NULL,
            related_name='bibtex_jobs',
            to='project_app.project'
        ),
    ),
]
```

---

## Testing

### Manual Test Workflow

**1. Create Test Project:**
```bash
# Via Django Admin or web UI
http://127.0.0.1:8000/ywatanabe/
# Create project: "test-scholar-integration"
```

**2. Upload Sample .bib:**
```bibtex
@article{watanabe2024,
  title={Test Paper},
  author={Watanabe, Y},
  journal={Test Journal},
  year={2024}
}
```

**3. Verify Enrichment:**
- Check job status page shows "Completed"
- Verify Gitea status card shows green success
- Click "View in Gitea Repository" link
- Confirm `/references/references.bib` exists in Gitea

**4. Verify Git History:**
```bash
cd /data/ywatanabe/test-scholar-integration
git log --oneline
# Should show: "Scholar: Enriched bibliography (1/1 papers enriched)"
```

---

## Troubleshooting

### Common Issues

**1. Gitea Commit Fails**

**Symptoms:** Yellow warning card, "Auto-commit to Gitea failed"

**Causes:**
- Project has no `git_clone_path`
- Git credentials not configured
- Gitea service down

**Solutions:**
```bash
# Check project has git_clone_path
python manage.py shell
>>> from apps.project_app.models import Project
>>> p = Project.objects.get(slug='my-project')
>>> print(p.git_clone_path)  # Should show path

# Check Gitea is running
curl http://localhost:3001/api/v1/version

# Re-run project creation signal to initialize git repo
```

**2. Enrichment Never Completes**

**Symptoms:** Job stuck in "Processing" status

**Causes:**
- Scholar pipeline error
- External API rate limits
- Missing dependencies

**Solutions:**
```bash
# Check job error message
python manage.py shell
>>> from apps.scholar_app.models import BibTeXEnrichmentJob
>>> job = BibTeXEnrichmentJob.objects.last()
>>> print(job.error_message)

# Check Scholar package installed
pip list | grep scitex-scholar
```

---

## Future Enhancements

### Planned Features

- [ ] **Real-time Progress**: WebSocket updates during enrichment
- [ ] **Selective Enrichment**: Choose which papers to enrich
- [ ] **Custom Enrichment**: Add user notes, tags to bibliography
- [ ] **Collaborative Enrichment**: Team members contribute enrichments
- [ ] **Enrichment History**: Track changes to individual entries
- [ ] **PDF Management**: Store PDFs in Git LFS
- [ ] **Citation Network**: Visualize citation relationships
- [ ] **Auto-Update**: Re-enrich periodically for updated citations

---

## Related Documentation

- **Django-Gitea Architecture**: `docs/DJANGO_GITEA_ARCHITECTURE.md`
- **Git Operations**: `apps/workspace_app/git_operations.py`
- **Scholar Pipeline**: External package `scitex.scholar`

---

## Summary

The Scholar-Gitea integration provides **automatic version control for enriched bibliographies**, ensuring that:

1. ✅ Research references are backed by rich metadata (abstracts, citations)
2. ✅ Bibliographies are version controlled in Gitea
3. ✅ Writer module has access to enhanced context for AI-assisted writing
4. ✅ Collaboration is enabled through standard Git workflows
5. ✅ Data is safely backed up and accessible

**Key Insight:** By auto-committing enriched .bib files to Gitea, we create a **single source of truth** for research references that all SciTeX modules (Scholar, Writer, Code, Viz) can access and build upon.

<!-- EOF -->
