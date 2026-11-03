# Container data permissions

`deployment/docker/common/scripts/root-init.sh` admits the data, configuration
and runtime directories before dropping privileges to the application account.
Its directory helpers must preserve existing accessible ownership and modes,
including private `0700` directories, non-executable `0600` files and access
provided by groups or ACLs.

Startup creates missing directories as `0700` for the application account. An
inaccessible existing mount root may be initialized only if it is empty and
root-owned. Other inaccessible existing directories require an explicit operator
repair. Symbolic links and non-directory entries at these bootstrap paths are
refused. Existing descendants are not recursively changed.

Image construction has a separate ownership boundary. At the end of
`deployment/docker/docker_prod/Dockerfile.prod`, after package installation and
import checks, initialize all ten image-owned bootstrap directories and the
existing image configuration files for the application identity. No deployment
mounts or host user data exist in that build step. Never move this recursive
image-state ownership preparation into runtime startup.

Precreate `/app/data` as well as `/app/data/users`: otherwise Docker can create
an inaccessible root-owned parent when attaching only the nested users mount.
`scripts/deploy/verify_default_bootstrap.py --constructor` checks the actual
image defaults and application access. The subsequent `--full-root-init` gate
admits only empty synthetic tmpfs users/config mounts, creates private fixtures,
runs the complete unchanged `/root-init.sh`, and verifies application access and
unchanged private modes, ownership and payload. Both Docker build gates run with
network disabled; they do not start Django, a database, a model or an app server.
A diagnostic derivative is not a deployment candidate. Qualify the canonical
image cold boot and actual staging/native smoke before tagging and publishing.

The previous bootstrap treated a directory without `755` permissions as broken,
then recursively applied `chmod 755` and ownership changes to the user tree.
That widened private directories and made private files readable and executable
by other local users. A private mode is not evidence of a damaged NAS mount.

Run the actual Bash behavior controls:

```bash
pytest tests/config/test_bootstrap_private_data.py tests/config/test_default_image_bootstrap.py
```

For deployment, also qualify fresh root-owned mounts and application credentials
inside an owned, isolated container. Use no host user-data mounts or external
network. Check mode, owner and content preservation, inaccessible-data refusal
and the mounted root's permissions after the actual service starts. Preserve
existing production ACLs; broader permission repairs are separate operations.
