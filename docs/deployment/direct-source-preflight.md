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
A bounded throwaway container installs all declared editables and extras
together with `uv pip install` into a normal system-site-packages virtual
environment, then runs `uv pip check`. This uses the same resolver as the
canonical development installer. This models the image plus editable overrides. The existing
dependency-floor and import probe runs in a separate network-disabled
container against those actual installed distributions. Serving package
roots, secrets, user data, service sockets and scheduler mounts are not
provided to either container. Git object stores are mounted read-only.

The environment lives on an owned Docker volume. Source snapshots and
labelled containers/volume are removed on completion or failure. Original
source identities are rechecked after preparation and probing. An installer
failure retains a private diagnostic log and refuses deployment. An
unmodelled Python-code overlay or inconsistent role source bind is refused.
Direct-source checks through `--via-ssh` or a substitute `--target` are
refused; run the canonical wrapper directly on the deployment host.

This gate checks Python dependency and import compatibility. It does not
replace image build qualification, frontend builds, startup tests, backups,
job-drain checks, browser verification or live integration acceptance.
