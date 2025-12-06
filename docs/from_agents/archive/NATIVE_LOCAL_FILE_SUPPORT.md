# Native Local File Support Strategy

**Created:** 2025-10-19
**Purpose:** Design document for seamless local filesystem integration with SciTeX Cloud

## Philosophy

SciTeX Cloud is **not just a web platform** - it's a **filesystem-aware research platform** that should work seamlessly with local files. Users should be able to:

1. Edit files locally with their preferred tools (VS Code, Emacs, Vim, etc.)
2. Have changes automatically reflected in the web UI
3. Access web features (Scholar, Viz, Writer) on their local files
4. Use git, scripts, and command-line tools naturally
5. Never worry about "upload/download" - files are **always local**

## Current State Analysis

### ✅ What Works
- Projects are stored at `./data/{username}/{project-slug}/`
- Files are **real filesystem files** (not database BLOBs)
- Web UI can read/write files directly
- Git clone integration works

### ❌ What Needs Improvement

1. **No automatic sync** - Manual refresh needed to see local changes
2. **Upload-centric UI** - Treats files like attachments, not native files
3. **No filesystem watching** - Changes outside web UI aren't detected
4. **Limited CLI tools** - No native command-line interface
5. **Web-first mentality** - Should be filesystem-first

## Architecture Design

### 1. Filesystem as Source of Truth

```
Principle: The filesystem IS the database for files
Database only stores: metadata, permissions, relationships
```

**Implementation:**
- `Project.data_location` → relative path only
- Never duplicate file content in DB
- Always read from filesystem when displaying
- Write directly to filesystem when editing

### 2. Bidirectional Sync Strategy

```python
# apps/workspace_app/filesystem_monitor.py

class FilesystemMonitor:
    """Monitor project directories for changes"""

    def watch_project(self, project):
        """Watch a project directory for changes using inotify/fsevents"""

    def on_file_created(self, file_path):
        """Handle new file creation"""
        # Update project.last_activity
        # Trigger any necessary indexing

    def on_file_modified(self, file_path):
        """Handle file modification"""
        # Update metadata
        # Invalidate caches

    def on_file_deleted(self, file_path):
        """Handle file deletion"""
        # Update project state
```

**Technologies:**
- Linux: `inotify` (pyinotify or watchdog)
- macOS: `fsevents`
- Windows: `ReadDirectoryChangesW`
- Cross-platform: `watchdog` library

### 3. CLI Tools for Native Operations

```bash
# scitex CLI tool (to be implemented)

# Create project from existing directory
scitex project create --from-dir ./my-research --name "My Research"

# Link existing git repository
scitex project link ./existing-project

# Open project in web UI
scitex project open my-research

# Run SciTeX modules on local files
scitex scholar search "neural networks" --project my-research
scitex viz plot ./data/results.csv --output ./figures/
scitex writer compile ./paper/manuscript/

# File operations (native)
cd ~/data/ywatanabe/my-project/
vim scripts/analysis.py           # Just edit normally
git commit -am "Update analysis"  # Git works natively
python scripts/analysis.py        # Run scripts directly
```

### 4. Web UI Enhancements

#### A. Real-time File Updates

```javascript
// Frontend: WebSocket connection for live updates
const projectWatcher = new WebSocket('/ws/project/{slug}/');
projectWatcher.onmessage = (event) => {
    const change = JSON.parse(event.data);
    if (change.type === 'file_modified') {
        // Refresh file tree
        // Show notification: "analysis.py was modified"
    }
};
```

#### B. Native File Browser

Instead of upload/download UI:
```
┌─ Project: testtest ──────────────────────┐
│ 📁 paper/                                │
│   📁 01_manuscript/                      │
│   📁 scripts/                            │
│     📄 crop_tif.py        (2.3 KB)      │  [Edit] [View] [Run]
│     📄 csv_to_latex.py    (1.8 KB)      │  [Edit] [View] [Run]
│   📁 tests/                              │
│ 📁 data/                                 │
│ 📁 results/                              │
│                                          │
│ [+ New File] [+ New Folder] [↻ Refresh] │
└──────────────────────────────────────────┘
```

#### C. Direct Edit with Auto-save

```python
# apps/project_app/views.py

@login_required
def edit_file_direct(request, username, slug, file_path):
    """Direct file editing with auto-save"""
    project_path = manager.get_project_path(project)
    full_path = project_path / file_path

    if request.method == 'POST':
        # Write directly to filesystem
        content = request.POST.get('content')
        full_path.write_text(content)

        # No database update needed!
        # Filesystem monitor will handle it

        return JsonResponse({'status': 'saved', 'timestamp': datetime.now().isoformat()})
```

### 5. Filesystem-First Operations

#### A. Project Creation from Existing Directory

```python
# apps/workspace_app/directory_manager.py

def import_existing_directory(self, source_path: Path, project_name: str) -> Project:
    """Import existing local directory as a SciTeX project"""

    # Option 1: Move directory
    target_path = self.base_path / slugify(project_name)
    shutil.move(source_path, target_path)

    # Option 2: Symlink (preserve original location)
    target_path.symlink_to(source_path.absolute())

    # Create project record
    project = Project.objects.create(
        name=project_name,
        owner=self.user,
        data_location=target_path.relative_to(self.base_path),
        directory_created=True
    )

    return project
```

#### B. Git-Native Operations

```python
# Users can work with git directly:
cd ./data/ywatanabe/testtest/
git status
git add .
git commit -m "Update analysis"
git push

# SciTeX Cloud detects changes automatically
# No manual sync needed!
```

### 6. Intelligent Caching

```python
# apps/workspace_app/file_cache.py

class FileMetadataCache:
    """Cache file metadata to avoid repeated filesystem calls"""

    def get_file_info(self, file_path: Path) -> dict:
        """Get cached file info or read from filesystem"""
        cache_key = f"file:{file_path}"

        # Check cache
        cached = cache.get(cache_key)
        if cached and self._is_fresh(cached, file_path):
            return cached

        # Read from filesystem
        stat = file_path.stat()
        info = {
            'size': stat.st_size,
            'modified': stat.st_mtime,
            'hash': self._quick_hash(file_path)  # For change detection
        }

        # Cache with filesystem mtime as validation
        cache.set(cache_key, info, timeout=3600)
        return info
```

## Implementation Plan

### Phase 1: Foundation (Week 1-2)
- [ ] Add `watchdog` dependency
- [ ] Create `filesystem_monitor.py` module
- [ ] Implement basic file watching for project directories
- [ ] Add WebSocket support for real-time updates

### Phase 2: CLI Tools (Week 3-4)
- [ ] Create `scitex` CLI package
- [ ] Implement `scitex project` commands
- [ ] Add project import/link functionality
- [ ] Create shell completion scripts

### Phase 3: Web UI Improvements (Week 5-6)
- [ ] Add real-time file tree updates
- [ ] Implement direct file editing
- [ ] Remove upload/download UI where not needed
- [ ] Add "Open in Terminal" buttons

### Phase 4: Advanced Features (Week 7-8)
- [ ] Symlink support for shared data
- [ ] Git operations through web UI
- [ ] Conflict detection and resolution
- [ ] Collaborative editing (operational transform)

## Technical Specifications

### File Watching Service

```python
# config/settings/settings_shared.py

FILESYSTEM_MONITOR = {
    'ENABLED': True,
    'WATCH_PATTERNS': ['*.py', '*.md', '*.tex', '*.csv', '*.json'],
    'IGNORE_PATTERNS': ['*.pyc', '__pycache__', '.git', 'node_modules'],
    'DEBOUNCE_SECONDS': 0.5,  # Group rapid changes
    'MAX_EVENTS_PER_SECOND': 100,
}
```

### WebSocket URL Configuration

```python
# config/urls.py

from django.urls import path
from apps.workspace_app.consumers import ProjectFileConsumer

websocket_urlpatterns = [
    path('ws/project/<slug:slug>/', ProjectFileConsumer.as_asgi()),
]
```

### Database Schema Updates

```python
# apps/project_app/models.py

class Project(models.Model):
    # Add fields for filesystem monitoring
    filesystem_monitoring_enabled = models.BooleanField(default=True)
    last_filesystem_scan = models.DateTimeField(null=True)
    filesystem_hash = models.CharField(max_length=64, blank=True)  # For change detection
```

## User Experience Examples

### Example 1: Researcher's Workflow

```bash
# Morning: Clone a project
cd ~/research
git clone git@github.com:lab/experiment-1.git

# Link to SciTeX Cloud
scitex project link ./experiment-1

# Work normally with local tools
cd experiment-1
vim scripts/analysis.py
python scripts/analysis.py

# Meanwhile, SciTeX Cloud:
# - Detects changes automatically
# - Updates web UI in real-time
# - Runs background tasks (if configured)
# - Keeps metadata in sync

# Afternoon: Use web features
scitex project open experiment-1  # Opens browser
# Use Scholar module to find references
# Use Viz module to create plots
# Use Writer module to draft paper

# All outputs go to local filesystem!
```

### Example 2: Collaborative Editing

```bash
# User A: Working locally
cd ~/data/ywatanabe/shared-project
vim paper/introduction.tex

# User B: Sees changes in web UI immediately
# Web UI shows: "introduction.tex was modified by ywatanabe (2 seconds ago)"
# Option to: [View Changes] [Pull Updates] [Edit Anyway]
```

### Example 3: Integration with External Tools

```bash
# Works seamlessly with any tool:
jupyter notebook                    # Jupyter sees all files
code .                             # VS Code works normally
make build                         # Makefiles work
docker-compose up                  # Docker sees files
pytest                             # Tests run on real files
```

## Benefits

1. **Natural Workflow**: Researchers use their preferred tools
2. **No Vendor Lock-in**: Files are always accessible, standard formats
3. **Better Performance**: No upload/download overhead
4. **Git-Friendly**: Version control works natively
5. **Scriptable**: Command-line tools enable automation
6. **Collaborative**: Multiple users, one filesystem
7. **Transparent**: What you see is what's on disk

## Migration Path

For existing projects:
1. No database migration needed (files already on filesystem)
2. Enable filesystem monitoring gradually (project by project)
3. Keep upload UI for backwards compatibility (hide by default)
4. Add deprecation warnings for old upload-centric workflows

## Security Considerations

1. **File permissions**: Enforce OS-level permissions
2. **Path traversal**: Validate all file paths strictly
3. **Symlink attacks**: Check symlink targets
4. **Resource limits**: Prevent watching too many files
5. **Rate limiting**: Limit filesystem operations per user

## Open Questions

1. **Multi-user conflicts**: How to handle simultaneous edits?
   - Option A: Last-write-wins (simple)
   - Option B: Operational Transform (complex, but better)
   - Option C: Git-style conflict markers

2. **Large repositories**: How to handle >10GB projects?
   - Option A: Disable watching for large projects
   - Option B: Selective watching (only important files)
   - Option C: Incremental scanning

3. **Remote filesystems**: Support NFS, SMB, cloud storage?
   - Challenge: Inotify doesn't work well on network filesystems
   - Solution: Periodic polling as fallback

## References

- Watchdog: https://github.com/gorakhargosh/watchdog
- inotify: https://man7.org/linux/man-pages/man7/inotify.7.html
- Django Channels: https://channels.readthedocs.io/
- Operational Transform: https://operational-transformation.github.io/

---

**Next Steps:**
1. Review this document with team
2. Prioritize features
3. Create detailed implementation tickets
4. Start with Phase 1 (Foundation)
