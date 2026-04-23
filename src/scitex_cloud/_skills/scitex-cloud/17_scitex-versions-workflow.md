# SciTeX Versions — Sync Workflow

## RULES: Never Sync Blind

1. **NEVER push local → remote without first checking remote state** (`diff`)
2. **NEVER pull remote → local without first checking local state** (`git status`)
3. **NEVER discard uncommitted changes without reading the diff contents**
4. **Always classify changes** before acting: improvement, artifact, or obsolete

## Workflow: Bidirectional Sync

### 1. Check BOTH sides first (MANDATORY)
```bash
# Check remote state
scitex dev versions diff                             # What's dirty on remote?

# Check local state
scitex dev versions list                             # Version alignment?
git status                                           # What's dirty locally?
```

### 2. Triage remote changes (MANDATORY before commit/discard)
For each dirty package on each host, read the diff and classify:

| Classification | Action | Example |
|----------------|--------|---------|
| **IMPROVEMENT** | Commit + pull | Real work: bug fixes, new features, config changes |
| **ARTIFACT** | Discard | `__pycache__`, `.pyc`, build outputs, `.egg-info` |
| **OBSOLETE** | Discard or archive | Dead experiments, abandoned branches |

```bash
# Read the actual diff contents before deciding
scitex dev versions diff --host nas --json

# Commit only improvements (per-package)
scitex dev versions commit --host nas -p scitex -m "feat: improvement from NAS" --confirm

# Discard artifacts only AFTER confirming contents (never blindly)
# ssh nas "cd ~/proj/scitex-python && git diff"           # READ FIRST
# ssh nas "cd ~/proj/scitex-python && git checkout -- ."   # Then discard
```

### 3. Pull remote → local
```bash
scitex dev versions pull                             # Preview first
scitex dev versions pull --confirm                   # Execute
```

### 4. Push local → remote
```bash
scitex dev versions sync                             # Preview first
scitex dev versions sync --confirm                   # Execute
scitex dev versions sync --local --confirm           # Local install
```

### 5. Verify
```bash
scitex dev versions list
scitex dev versions diff                             # Should be clean now
```

### Full round-trip (typical)
```bash
# 1. Check both sides
scitex dev versions diff
git status
# 2. Triage + commit real improvements on remote
scitex dev versions commit --host nas --confirm
# 3. Pull to local
scitex dev versions pull --confirm
# 4. Do local work...
# 5. Check remote again before pushing
scitex dev versions diff
# 6. Push to remote
scitex dev versions sync --confirm
# 7. Verify
scitex dev versions list
```

### Manual workflow (if needed)
```bash
# Push changes to origin
for repo in scitex-python scitex-cloud figrecipe openalex-local crossref-local scitex-writer scitex-dataset socialia; do
    cd ~/proj/$repo && git push origin develop 2>/dev/null || git push origin main
done

# Verify
scitex dev versions list
```

## See also
- [16_scitex-versions.md](16_scitex-versions.md) — Commands reference and Python API
- [18_scitex-versions-release.md](18_scitex-versions-release.md) — Version increment, tag syncing, troubleshooting
