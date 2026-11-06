# Development source preflight

This host-tool follow-up to Hub 0.22.0a6 adds support for the canonical
development Compose setup. The published 0.22.0a6 tag predates this support.
Production image-only and staging clone-overlay policies remain unchanged.

Run `scripts/deploy/compose.sh dev up ...` on the Docker host. The shared
pre-up gate resolves the actual Compose configuration, recognizes the
canonical development entrypoint and inspects the package binds shared by
Django, worker and beat. It reads package roots and extras from
`deployment/docker/docker_dev/install_ecosystem.sh`, including Hub and the
umbrella with `[all]`. Missing non-package sibling directories are skipped
at the same package-validity boundary as that installer.

The gate requires clean Git repository roots. It snapshots exact commits into
owned shared clones, preserving Git history for normal SCM versioning.
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
