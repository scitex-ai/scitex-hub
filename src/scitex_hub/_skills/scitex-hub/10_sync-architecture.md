---
description: |
  [TOPIC] Sync Architecture — Local ↔ Gitea ↔ Workspace
  [DETAILS] Three-way sync architecture between Local, Gitea, and Workspace. CLI commands for push/pull (git) and workspace push/pull (files). Conflict detection and resolution..
tags: [scitex-hub-sync-architecture]
---

# Sync Architecture — Local ↔ Gitea ↔ Workspace

## Three Nodes, Three Relationships

```
            Gitea
           (source of truth)
          ╱              ╲
    push/pull          w2g/g2w
    (git)              (server-side git)
        ╱                  ╲
     Local ──────────── Workspace
  (dev machine)  workspace push/pull  (server-side)
                  (rsync/files)
```

Each relationship is independent and explicit. No hidden sync.

## Commands

### Git operations (committed changes)

```bash
scitex cloud push              # git push to Gitea
scitex cloud push origin main  # push specific branch
scitex cloud pull              # git pull from Gitea
scitex cloud pull origin main  # pull specific branch
```

These are thin wrappers around `git push/pull`. They work from
**anywhere** — laptop or workspace. "Push" always means "push to Gitea."

### File sync (working tree, Dropbox-style)

```bash
scitex cloud workspace push                    # sync local → workspace
scitex cloud workspace push ywatanabe/my-proj  # explicit repo
scitex cloud workspace push --dry-run          # preview changes
scitex cloud workspace pull                  # sync workspace → local
scitex cloud workspace pull --dry-run        # preview changes
```

These sync **uncommitted working files** between local machine and workspace.

**Conflict detection:** Both sides' checksums are compared against a saved
`.scitex-sync-state.json` from the last successful sync:

| Scenario | Action |
|----------|--------|
| Only one side changed | Overwrite stale copy |
| Both sides changed | Keep both: original syncs, other saved as `.conflict-<timestamp>` |
| Neither changed | Skip (already in sync) |

**On workspace:** `workspace push` and `workspace pull` error with a hint:
```
You're already on the workspace.
Did you mean: scitex cloud push
```

### Status

```bash
scitex cloud workspace status  # show divergence across all three
```

The old spellings (`sync-to`, `sync-from`, `sync-status`, `ss`) are
deprecated warn-phase aliases, removed in v0.20.

Output:
```
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Pair              ┃ Status                 ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Local ↔ Gitea     │ ↑2 ahead, ↓0 behind    │
│ Workspace ↔ Gitea │ in sync                │
└───────────────────┴────────────────────────┘
```

## Typical Workflows

### Developer edits locally, wants to see changes in workspace

```bash
# Edit files locally...
scitex cloud workspace push          # files appear in workspace immediately
# Verify in browser...
scitex cloud push             # commit and push to Gitea when ready
```

### User edits in web UI, developer wants the changes

```bash
scitex cloud workspace pull        # pull workspace files to local
# If conflicts: resolve .conflict-* files manually
scitex cloud push             # push resolved version to Gitea
```

### Full round-trip

```bash
scitex cloud workspace status # check state
scitex cloud workspace pull   # get workspace changes
# resolve any conflicts...
git add -A && git commit -m "merge workspace edits"
scitex cloud push             # push to Gitea
```

## Conflict Files

When both sides change the same file:

```
data/config.yaml                              ← synced version (winner)
data/config.conflict-20260324T120000.yaml     ← other side's version
```

The user must manually resolve and delete the `.conflict-*` file.
This is the same model as Dropbox "conflicted copy."

## Implementation

- `_cli/sync.py` — CLI commands (push-project, pull-project, workspace push/pull/status)
- `_cli/_sync_engine.py` — Conflict-aware file sync engine
- State tracking: `.scitex-sync-state.json` (checksums from last sync)
- Remote file listing: SSH + `find` + `sha256sum`
- File transfer: `scp` per file (not rsync — enables per-file conflict handling)

# EOF
