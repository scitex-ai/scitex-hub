# Development source preflight

This host-tool follow-up to Hub 0.22.0a6 adds support for the canonical
development Compose setup. The published 0.22.0a6 tag predates this support.
Production image-only and staging clone-overlay policies remain unchanged.
The follow-up also pins the available `electron-to-chromium` 1.5.477 build
dependency: npm advertised 1.5.478 while its tarball returned HTTP 404.
Already baked production bundles do not fetch this dependency at startup.

Run `scripts/deploy/compose.sh dev up ...` on the Docker host. The shared
pre-up gate resolves the actual Compose configuration, recognizes the
canonical development entrypoint and inspects the package binds shared by
Django, worker and beat. It reads package roots and extras from
`deployment/docker/docker_dev/install_ecosystem.sh`, including Hub and the
umbrella with `[all]`. Missing non-package sibling directories are skipped
at the same package-validity boundary as that installer.

The gate requires Git repository roots with no uncommitted source edits.
Normal npm startup may modify or create `package-lock.json` beside a tracked
`package.json`. These generated JSON locks are the only exception: their exact
bytes, Git status and hashes enter the owned snapshot and are rechecked after
installation and probing. Staged changes, other untracked files, symlinks and
locks over 64 MiB are refused. Source files are never reset or discarded.
The gate snapshots exact commits and those generated locks into owned shared
clones, preserving normal Git history and dirty state for SCM versioning.
A bounded throwaway container starts from the exact selected image. It
installs all declared editables and extras together with the canonical
`uv pip install --system` command, followed by `uv pip check --system`.
This preserves the image's existing dependency graph unless the normal
resolver needs to change it. No virtual environment, substituted package
metadata or reduced extra set stands in for the future runtime.
The existing dependency-floor and import probe runs against that same
installed container after its network has been disconnected and verified.
Serving package roots, secrets, user data, service sockets and scheduler
mounts are not provided. Git object stores are mounted read-only.

Installer caches live on an owned Docker volume. Source snapshots and
labelled containers/volume are removed on completion or failure. Original
source identities are rechecked after preparation and probing. An installer
failure retains a private diagnostic log and refuses deployment. An
unmodelled Python-code overlay or inconsistent role source bind is refused.
Direct-source checks through `--via-ssh` or a substitute `--target` are
refused; run the canonical wrapper directly on the deployment host.

This gate checks Python dependency and import compatibility. It does not
replace image build qualification, frontend builds, startup tests, backups,
job-drain checks, browser verification or live integration acceptance.
