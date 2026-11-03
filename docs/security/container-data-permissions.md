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

The previous bootstrap treated a directory without `755` permissions as broken,
then recursively applied `chmod 755` and ownership changes to the user tree.
That widened private directories and made private files readable and executable
by other local users. A private mode is not evidence of a damaged NAS mount.

Run the actual Bash behavior controls:

```bash
pytest tests/config/test_bootstrap_private_data.py
```

For deployment, also qualify fresh root-owned mounts and application credentials
inside an owned, isolated container. Use no host user-data mounts or external
network. Check mode, owner and content preservation, inaccessible-data refusal
and the mounted root's permissions after the actual service starts. Preserve
existing production ACLs; broader permission repairs are separate operations.
