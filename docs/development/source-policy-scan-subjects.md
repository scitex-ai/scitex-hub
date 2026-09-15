# Source-policy scan subjects

Repository-wide policy gates must scan staged Git-index blobs through
`tests.tracked_source.tracked_source_files`, not recursively walk the checkout.
That makes local pre-commit and fresh-checkout CI evaluate the same bytes:
staged additions/edits are included, staged deletions are absent, unstaged edits
are excluded, conflicts fail closed, and an empty requested corpus is an error.

Migrated repository policy/security sweeps:

- copy-on-edit backup names
- compose credentials in command/entrypoint argv
- canonical public repository URLs
- absolute GitHub links in templates
- insecure deserialization
- prefix-string path containment
- session-authenticated CSRF exemptions
- network Git calls without credential environments
- usable credential defaults
- interactive Click prompt call sites
- legacy project-picker imports

The other recursive walkers under `tests/` exercise temporary/runtime
filesystems, installed packages, generated output, or bounded feature fixtures;
they are not assertions about the repository's tracked source corpus.

Untracked working-tree dirt cannot exist in a normal CI checkout and is not part
of any CI claim. Run `make check-source-dirt` locally. It uses NUL-delimited Git
output, excludes ignored files, reads no file contents, and reports escaped path
names only. Runtime `data/`, `.old/`, linked `.worktrees/`, ignored files, and
other non-index material therefore cannot pollute tracked-source scans.
