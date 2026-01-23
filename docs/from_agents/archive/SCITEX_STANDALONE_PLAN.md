# SciTeX Standalone Application - Implementation Plan

## Vision

**One executable. Complete research workflow. Zero setup.**

```
scitex.exe (Windows) / scitex.app (macOS) / scitex.AppImage (Linux)
  ↓
Double-click
  ↓
Complete research platform running locally at http://localhost:5000
```

## The Complete SciTeX Suite

Based on your code references:

```
SCITEX_SCHOLAR   → Literature management & bulk PDF downloads
SCITEX_WRITER    → Scientific writing (LaTeX + AI)
SCITEX_CODE      → Data analysis workflows
SCITEX_VIZ       → Publication-quality graphics
SCITEX_ENGINE    → Emacs + Claude Code orchestration
SCITEX_CLOUD     → Web platform (companion, not replacement)
```

## Product Strategy

### Primary Product: **scitex.exe** (Local Desktop App)
- Standalone executable
- No installation complexity
- Full automation with user's credentials (local only)
- All research workflow tools
- Runs completely offline

### Secondary Product: **SciTeX Cloud** (Web Companion)
- Marketing & documentation
- Community features
- Optional cloud sync
- Collaboration tools
- Download center for scitex.exe

## Phase 1: Scholar Standalone (MVP)

### Goal
Prove the standalone executable approach with Scholar module.

### Features
```
scitex-scholar.exe opens web UI with:

1. Bulk BibTeX Processing
   - Upload .bib file
   - Configure: Project name, workers (1-8)
   - One-click: "Process All Papers"
   - Progress: Real-time updates
   - Result: All PDFs downloaded & organized

2. Single Paper Download
   - Input: DOI or title
   - One-click: "Download Paper"
   - Result: PDF + metadata in library

3. Library Management
   - Browse downloaded papers
   - Search local library
   - Export bibliographies
   - Organize into projects

4. Settings
   - Institutional credentials (OpenAthens/SSO)
   - Chrome profile selection
   - Download preferences
   - Storage location
```

### Technical Architecture

```
scitex-scholar.exe
├── Embedded Components
│   ├── Python 3.11 runtime
│   ├── scitex.scholar module (from ~/proj/scitex_repo)
│   ├── Playwright + Chromium browser
│   ├── Flask web server
│   └── SQLite database
│
├── Web UI (localhost:5000)
│   ├── HTML/CSS/JS (modern SPA)
│   ├── File upload handling
│   ├── Real-time progress (WebSocket)
│   └── Library browser
│
└── Background Workers
    ├── ScholarPipelineBibTeX runner
    ├── PDF download queue
    └── Progress reporting
```

### File Structure

```
scitex-scholar/
├── src/
│   ├── web/                      # Web UI layer
│   │   ├── app.py               # Flask application
│   │   ├── static/              # CSS, JS
│   │   ├── templates/           # HTML templates
│   │   └── api/                 # REST API endpoints
│   │
│   ├── services/                # Business logic
│   │   ├── scholar_service.py   # Wraps scitex.scholar
│   │   ├── job_service.py       # Background jobs
│   │   └── library_service.py   # Library operations
│   │
│   └── main.py                  # Entry point
│
├── build/                       # Build configuration
│   ├── scitex-scholar.spec     # PyInstaller spec
│   ├── icon.ico                # Application icon
│   └── installer.nsi           # NSIS installer (Windows)
│
├── requirements.txt
└── README.md
```

### User Experience Flow

**Initial Launch:**
```
1. User downloads scitex-scholar.exe (200MB)
2. Double-clicks to run
3. Browser opens to http://localhost:5000
4. Welcome screen: "Setup your institution" (one-time)
5. User enters institutional email/password
6. Test authentication: "✓ Connected to University of Melbourne"
7. Ready to use!
```

**Daily Usage:**
```
1. User gets 300-paper BibTeX from AI2 Scholar QA
2. Opens scitex-scholar (already running in system tray)
3. Drags neurovista.bib into upload area
4. Clicks "Process BibTeX"
5. Configures:
   - Project: "neurovista"
   - Workers: 8
   - Download PDFs: Yes
6. Clicks "Start Processing"
7. Progress bar: "Processing 45/300 papers (15%)..."
8. Goes for coffee (30 minutes)
9. Returns: "✓ Complete! 298/300 PDFs downloaded"
10. Browse library, organize papers, export
```

**Credentials:**
- Stored locally in encrypted SQLite
- Never sent to any server
- User can view/edit in Settings
- Can work completely offline

## Phase 2: Full SciTeX Suite

### scitex.exe - Complete Platform

```
Main Dashboard:
┌─────────────────────────────────────────────────────────┐
│ 🎓 SciTeX - Research Operating System                   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ [🔍 Scholar]  [✍️ Writer]  [💻 Code]  [📊 Viz]  [⚙️ Engine]│
│                                                          │
│ Active Project: neurovista                              │
│ ├─ Papers: 298                                          │
│ ├─ Manuscript: draft_v3.tex                             │
│ ├─ Analysis: spike_detection.ipynb                      │
│ └─ Figures: 12 figures                                  │
│                                                          │
│ Recent Activity:                                        │
│ • Downloaded 45 PDFs (Scholar)                          │
│ • Updated manuscript methods (Writer)                   │
│ • Generated Figure 3 (Viz)                              │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Integration Between Modules

**Scholar → Writer:**
```
User: Download 300 papers in Scholar
      ↓
Writer: "Import references from Scholar library?"
      ↓
One-click: All citations available in LaTeX
```

**Code → Viz:**
```
User: Analyze data in Code module
      ↓
Viz: "Create publication figure?"
      ↓
One-click: Export to Writer manuscript
```

**Engine (Emacs + Claude Code):**
```
User: Working in Emacs
      ↓
Claude: "Need a paper on transformers?"
      ↓
Scholar: Searches, downloads, returns to Emacs
      ↓
Seamless integration!
```

## Technical Implementation

### Build System

```bash
# pyinstaller/scitex.spec

a = Analysis(
    ['src/main.py'],
    pathex=['/home/ywatanabe/proj/scitex_repo/src'],
    binaries=[],
    datas=[
        ('src/web/templates', 'templates'),
        ('src/web/static', 'static'),
        ('.playwright', 'playwright'),  # Bundled Chromium
    ],
    hiddenimports=[
        'scitex.scholar',
        'scitex.code',
        'scitex.viz',
        # All scitex modules
    ],
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='scitex',
    icon='build/scitex-icon.ico',
    console=False,  # No console window
    onefile=True    # Single .exe file
)
```

### Size Optimization

**Expected sizes:**
- scitex-scholar.exe: ~200MB (Python + Playwright + Chromium)
- scitex.exe (full): ~400MB (All modules + dependencies)

**Optimization:**
```bash
# Use UPX compression
pyinstaller --upx-dir=/path/to/upx

# Result: ~250MB compressed
```

**Compare to:**
- Anaconda: ~500MB
- RStudio: ~300MB
- VS Code: ~200MB

→ scitex.exe at 400MB is reasonable!

## Storage Architecture

### Local-First with Optional Sync

```
User's Machine:
~/SciTeX/
├── library/                  # Scholar papers
│   ├── MASTER/              # Deduplicated PDFs
│   └── neurovista/          # Project symlinks
├── projects/                # Writer projects
│   ├── neurovista/
│   │   ├── main.tex
│   │   ├── figures/
│   │   └── references.bib   # Auto-populated from Scholar!
│   └── deep_learning_review/
├── analysis/                # Code notebooks
└── config/                  # Settings, credentials (encrypted)
```

**Optional Cloud Sync:**
```
User: "Sync neurovista project to cloud"
  ↓
Uploads: Papers, manuscript, analysis, figures
  ↓
Available at: https://scitex.ai/projects/ywatanabe/neurovista/
  ↓
Collaborators can: View, comment, suggest edits
  ↓
User syncs back: Gets collaborator changes locally
```

## Business Model

### Free Tier (Desktop App)
- ✅ scitex.exe download (free, open source)
- ✅ Unlimited local use
- ✅ All features
- ✅ No cloud sync

### Pro Tier ($89/year)
- ✅ Everything in Free
- ✅ Cloud sync (50GB)
- ✅ Collaboration features
- ✅ Access from anywhere
- ✅ Mobile web viewer

### Institutional Tier (Custom)
- ✅ Everything in Pro
- ✅ Unlimited users
- ✅ Institutional deployment (MSI installer)
- ✅ LDAP/SSO integration
- ✅ Priority support
- ✅ On-premise option

## Competitive Positioning

**vs. Existing Tools:**

| Feature | Zotero | Mendeley | Overleaf | **SciTeX** |
|---------|---------|----------|----------|------------|
| Bulk PDF download | Manual | Manual | N/A | ✅ **Automated (300 papers)** |
| Institutional auth | Extension | Extension | N/A | ✅ **Built-in** |
| Writing integration | Plugin | Plugin | ✅ Yes | ✅ **Seamless** |
| Data analysis | ❌ No | ❌ No | ❌ No | ✅ **Integrated** |
| Visualization | ❌ No | ❌ No | ❌ No | ✅ **Built-in** |
| 100% Open Source | ✅ Yes | ❌ No | ❌ No | ✅ **Yes** |
| Local-first | ✅ Yes | ⚠️ Hybrid | ❌ Cloud | ✅ **Yes** |

**Unique selling point:**
> "The ONLY tool that automates downloading 300 papers with one click"

## Implementation Roadmap

### Milestone 1: Scholar Standalone (Month 1)
**Week 1:**
- [ ] Create Flask web UI for Scholar
- [ ] Wrap ScholarPipelineBibTeX
- [ ] Progress reporting via WebSocket
- [ ] Library browser UI

**Week 2:**
- [ ] Package with PyInstaller
- [ ] Test on Windows/Mac/Linux
- [ ] Credential encryption
- [ ] Auto-update mechanism

**Week 3:**
- [ ] Polish UI/UX
- [ ] Error handling
- [ ] User documentation
- [ ] Create installer

**Week 4:**
- [ ] Beta testing
- [ ] Bug fixes
- [ ] Prepare release

**Deliverable:** scitex-scholar-v1.0.exe

### Milestone 2: Add Writer Module (Month 2)
- [ ] Integrate Writer UI (LaTeX editor)
- [ ] Reference picker from Scholar library
- [ ] Live preview
- [ ] Export to Overleaf

**Deliverable:** scitex-v2.0.exe (Scholar + Writer)

### Milestone 3: Add Code & Viz (Month 3)
- [ ] Jupyter notebook interface
- [ ] Matplotlib/Plotly integration
- [ ] Export figures to Writer

**Deliverable:** scitex-v3.0.exe (Complete suite)

### Milestone 4: Cloud Integration (Month 4)
- [ ] Sync API in Django
- [ ] Web viewer at scitex.ai
- [ ] Collaboration features
- [ ] Mobile access

**Deliverable:** scitex.exe + scitex.ai integration

## Distribution Strategy

### Release Channels

**GitHub Releases:**
```
github.com/ywatanabe1989/scitex/releases
├── scitex-v1.0-windows.exe (200MB)
├── scitex-v1.0-macos.dmg (180MB)
├── scitex-v1.0-linux.AppImage (190MB)
└── checksums.txt
```

**Auto-update:**
```python
# Built-in updater
Checks GitHub releases API daily
Downloads new version in background
Prompts: "Update available - Install now?"
```

**Installation Methods:**

1. **Direct download** (github.com/scitex/releases)
2. **Chocolatey** (Windows): `choco install scitex`
3. **Homebrew** (macOS): `brew install scitex`
4. **Snap** (Linux): `snap install scitex`

## Technical Challenges & Solutions

### Challenge 1: Executable Size (~400MB)

**Solutions:**
- Use PyInstaller with UPX compression (~250MB)
- Lazy-load Playwright browser (download on first use)
- Modular: scitex-scholar.exe (200MB) vs scitex-full.exe (400MB)

### Challenge 2: Platform Support

**Windows:**
- ✅ PyInstaller works well
- ✅ NSIS installer for professional feel
- ✅ Largest user base

**macOS:**
- ⚠️ Code signing required ($99/year Apple Developer)
- ⚠️ Notarization for Gatekeeper
- Solution: Provide .app bundle with instructions

**Linux:**
- ✅ AppImage (easiest)
- ✅ Snap package
- ✅ Users typically more technical

### Challenge 3: Browser Automation in Packaged App

**Solution:**
```python
# Playwright with bundled browser
playwright.chromium.launch(
    executable_path=bundled_chromium_path
)

# Bundle browser in exe
# Or: Download on first run (better - smaller initial download)
```

### Challenge 4: Auto-Updates

**Solution:**
```python
# GitHub Releases API
import requests

def check_for_updates():
    response = requests.get(
        'https://api.github.com/repos/ywatanabe1989/scitex/releases/latest'
    )
    latest_version = response.json()['tag_name']

    if latest_version > current_version:
        download_update(latest_version)
```

## Development Environment Setup

### Building the Executable

```bash
# 1. Install build tools
pip install pyinstaller

# 2. Build
cd ~/proj/scitex-standalone
pyinstaller scitex.spec --clean

# 3. Result
dist/scitex.exe  # Ready to distribute!

# 4. Test
./dist/scitex.exe  # Should open browser to localhost:5000
```

### Testing Matrix

| OS | Python | Browser | Status |
|----|--------|---------|--------|
| Windows 11 | 3.11 | Chromium | ✅ Primary |
| macOS 14 | 3.11 | Chromium | ⚠️ Test |
| Ubuntu 22.04 | 3.11 | Chromium | ⚠️ Test |

## SciTeX Cloud Integration

### Role of Django Web App

**NOT a replacement, but a companion:**

```
scitex.ai:
├── Landing page & marketing
├── Documentation & tutorials
├── Download scitex.exe
├── Community forum
├── API for sync (optional)
└── Collaboration features
```

### Sync API (Optional Feature)

```python
# apps/api/v1/sync/views.py

@api_view(['POST'])
@login_required
def sync_library(request):
    """
    Receive library sync from local scitex.exe

    User's local scitex.exe calls:
    POST /api/v1/sync/library/
    Body: {
        'project': 'neurovista',
        'papers': [...],  # Metadata only
        'pdfs': <multipart>  # Actual PDFs
    }
    """
    project = request.data['project']
    papers = request.data['papers']

    # Store in user's cloud library
    for paper in papers:
        CloudPaper.objects.update_or_create(
            user=request.user,
            doi=paper['doi'],
            defaults={
                'title': paper['title'],
                'metadata': paper,
                # ...
            }
        )

    return Response({'synced': len(papers)})
```

**User controls sync:**
```
scitex.exe → Settings → Cloud Sync
  ├─ [ ] Enable cloud sync
  ├─ Project: neurovista
  ├─ Sync: Metadata + PDFs / Metadata only
  └─ [Sync Now] button
```

## Advantages of This Approach

### For Users
- ✅ **Zero setup complexity** - Download → Run → Research
- ✅ **Complete privacy** - Credentials never leave their machine
- ✅ **Works offline** - No internet required
- ✅ **Full automation** - Batch processing power
- ✅ **Fast** - Local processing, no network latency

### For You (Development)
- ✅ **Leverage existing code** - scitex.scholar already works!
- ✅ **Simple web UI** - Just Flask + HTML forms
- ✅ **No server infrastructure** - Runs on user machines
- ✅ **Lower costs** - No compute/storage costs
- ✅ **Easier to maintain** - One codebase

### For Your Mission
- ✅ **100% open source** - Exe is just packaged Python
- ✅ **Transparent** - User can see all code
- ✅ **Self-hostable** - IS self-hosted (on user's machine)
- ✅ **No vendor lock-in** - Works without cloud
- ✅ **Privacy-first** - Data stays local

## Comparison: Web App vs Standalone

### Web App (Server-Side)
**Pros:**
- Access from anywhere
- No installation
- Easy updates

**Cons:**
- ❌ Must store credentials (trust issue)
- ❌ Server costs for browser automation
- ❌ Scalability limits
- ❌ Privacy concerns
- ❌ Institutional policy violations

### Standalone App (Local)
**Pros:**
- ✅ Full privacy (credentials local)
- ✅ Full automation (no restrictions)
- ✅ No server costs
- ✅ Works offline
- ✅ Institutional approval easier

**Cons:**
- Requires download (~200-400MB)
- Platform-specific builds
- Updates need redistribution

**Verdict:** For your use case (bulk automation with credentials), **standalone is clearly better**.

## Next Steps

### Immediate (This Week)
1. **Create proof-of-concept:**
   - Flask UI wrapping ScholarPipelineBibTeX
   - Test locally (not packaged yet)
   - Validate the approach

2. **Design UI mockups:**
   - Scholar dashboard
   - Upload interface
   - Progress view
   - Library browser

3. **Plan packaging:**
   - PyInstaller configuration
   - Icon design
   - Installer script

### Short-term (This Month)
1. Build scitex-scholar-standalone.exe
2. Beta test with early users
3. Gather feedback
4. Iterate

### Medium-term (Next 3 Months)
1. Add Writer module
2. Add Code module
3. Add Viz module
4. Complete scitex.exe suite

### Long-term (Next 6 Months)
1. Cloud sync integration
2. Collaboration features
3. Mobile companion app
4. Browser extension (optional)

## Success Metrics

**Week 1:** Working prototype (Flask UI + scholar)
**Week 2:** Packaged exe that runs
**Week 4:** 10 beta testers using it
**Month 2:** 100 users, gather feedback
**Month 3:** Public v1.0 release
**Month 6:** 1000+ downloads, proven product-market fit

## Risk Mitigation

### Risk: Exe files are scary (malware concerns)

**Mitigation:**
- Code signing certificate
- Open source (users can build themselves)
- Checksums + GPG signatures
- GitHub releases (trusted source)

### Risk: Platform-specific bugs

**Mitigation:**
- Start with Windows (70% of users)
- Add macOS/Linux incrementally
- Community testing
- Clear bug reporting

### Risk: Large download size

**Mitigation:**
- Clear value proposition (worth 400MB)
- Modular: Scholar-only (~200MB) option
- Fast mirrors/CDN

## Conclusion

**scitex.exe is the RIGHT product for your vision:**

1. Solves the hard problem (bulk automation)
2. Preserves privacy (local credentials)
3. Aligns with values (open, transparent, local-first)
4. Leverages existing work (scitex.scholar already works!)
5. Better business model (lower costs, clearer value)

**SciTeX Cloud becomes the companion:**
- Discover the tool
- Download scitex.exe
- Optional sync & collaboration
- Community hub

**This is how you beat competitors** - Give researchers what they actually need (automation) in a way they can trust (local, open source).

---

**Ready to build scitex-scholar-standalone.exe prototype?**

Generated: 2025-10-15
Author: Claude Code
Status: Strategic Plan - Ready for Implementation
