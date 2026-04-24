# v0.17.1-alpha - 2026-04-21

## Deploy reliability + Writer v2 wrapper

### Deploy — rebuild.sh root-cause fix
The `make env=dev rebuild` step 6 ("Fixing Apptainer sandbox permissions") had been silently masking real failures for a long time: the sandbox contains ~2.4k files owned by sub-UIDs from prior `apptainer --fakeroot` sessions that `ywatanabe` cannot chmod from the host, so `chmod -R a+rX ... || echo warning` always emitted the warning and still printed "Sandbox permissions fixed".

- **Preflight** (fail fast before the long docker build): abort when `apptainer` is missing or `/etc/subuid` lacks an entry for `$USER`, with a one-liner fix suggestion (`sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 $USER`).
- **Correct chmod path**: run chmod *inside* a contained fakeroot namespace, where root-in-namespace owns the sub-UID files:
  ```
  apptainer exec --fakeroot --writable \
    --contain --no-home --no-mount home,tmp,cwd \
    <sandbox> find / -xdev \
      -not -path '/proc*' -not -path '/sys*' -not -path '/dev*' \
      -exec chmod a+rX {} +
  ```
  - `--contain --no-home --no-mount home,tmp,cwd` prevents apptainer's default bind of host `$HOME` / `$TMPDIR` / `$CWD`, so chmod never walks into host files (previously it tried to chmod `~/.scitex/scholar/cache/...` which are host files).
  - `-xdev` + path exclusions skip `/proc`, `/sys`, `/dev` kernel pseudo-filesystems that cannot be chmod'd by anyone.
- **Fail loud** on real errors instead of silent-continue.
- **Performance**: step drops from effectively-hung (or minutes of irrelevant `~/.scitex/...` warnings) to ~35 s, exit 0.

### CI — sibling `scitex-writer` checkout
- Install `scitex-writer` as a sibling repo during CI so the writer v2 wrapper can import it; when absent, `apps/workspace/writer_app/urls.py` logs a skip instead of raising. Unsticks CI on forks without the sibling repo.

### Writer app — v2 thin wrapper (fix #146)
- `apps/workspace/writer_app` now consumes `scitex_writer._django` as a thin wrapper. v2 routes mount only when the module is installed, keeping the v1 path intact for existing deployments.

## Upgrade notes
- No migration required.
- If `make env=dev rebuild` has been failing silently on the Apptainer step, the new preflight will now print an explicit fix command up front.
