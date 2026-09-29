# NAS-02 → compute-01 storage canary runbook

**Status:** Stage-1 plan; do not apply until the Storage Broker typed contract,
rollback path, and operator approval gate are green.

This canary introduces a new dedicated NFS export and a temporary mount on
`scitex-compute-01`. It does **not** replace or modify the current SSHFS mounts,
other compute nodes, existing homes, or live Hub data.

## Fixed scope

- NAS: `scitex-nas-02`
- Canary client: `scitex-compute-01`
- Service mountpoint: `/scitex-hub`
- Durable directories: `home`, `projects`, `datasets`
- Node-local scratch remains `/scratch`
- Test identity: a newly allocated `ComputeIdentity` UID/GID in 20000–59999
- No customer account or production project participates

## Preconditions

1. `scitex-hub dev doctor --json` names every missing leaf package/remedy.
2. `scitex-hub dev setup plan --json` is reviewed.
3. `scitex-hub dev storage canary plan --json` is archived with the run.
4. `scitex-storage` ships the typed `validate_storage_contract` capability and
   its runtime result—not package metadata alone—drives `storage validate`.
5. The NFS export source and client allowlist are explicit; no wildcard client.
6. Export uses root-squash. The existing wildcard `Public`/no-root-squash export
   is not reused.
7. The NAS-side provisioner owns directory/owner/mode/quota mutation. Client
   root does not receive that authority.
8. Existing `/mnt/scitex-nas-*` SSHFS units remain untouched.
9. `/scitex-hub` is absent or an empty local mountpoint; it is not a symlink.
10. Rollback has been dry-reviewed before apply.

## Apply phases

### A. NAS-side provisioner

The provisioner performs typed operations only:

```text
create_home(identity_id, idempotency_key)
set_quota(resource_id, bytes, inodes, idempotency_key)
verify_resource(resource_id)
```

It resolves canonical paths and numeric UID/GID from trusted state. It does not
accept raw paths, shell strings, argv, or caller-supplied numeric identities.
Every mutation records actor, idempotency key, before/after state, executor
result, and readback.

For the quota-denial probe, use a small temporary canary limit rather than
writing 32 GB. After the denial is proven, set the product limit to 32 GB and
read it back.

### B. Dedicated NFS export

Create a dedicated export for the SciTeX storage tree only. Requirements:

- allow `scitex-compute-01` storage-network address only during canary;
- root-squash;
- read/write, stable numeric UID/GID;
- no wildcard client;
- do not expose the entire NAS volume;
- do not place a generic NAS administrator credential in Hub.

The exact QNAP export operation belongs to the NAS executor/runbook and must be
read back from NAS configuration before continuing.

### C. compute-01 mount

Create a root-owned local mountpoint whose unmounted state is fail-closed. The
managed NFS mount must target `/scitex-hub` directly. Do not add permanent
`/mnt -> /scitex-hub -> /customer` layers.

The node-side projector verifies the exact mount source, filesystem type, and
mountpoint before producing any runtime bind manifest.

## Acceptance probes

Archive structured output for every probe.

1. `findmnt` reports the dedicated source mounted exactly at `/scitex-hub` with
   NFS/NFSv4 type.
2. `/scitex-hub/{home,projects,datasets}` exist on the mounted export.
3. The canary UID can create/read/write within its provisioned home.
4. A different unprivileged UID cannot traverse/read/write that home.
5. Client root cannot change NAS ownership/quota through the root-squashed
   export.
6. NAS-side provisioner can idempotently re-run the same request and read back
   the same owner/mode/quota.
7. A small temporary quota rejects a real write beyond the limit.
8. The final 32 GB capacity and inode limit are read back from NAS authority.
9. `/scratch` remains a separate node-local filesystem.
10. A generated runtime manifest includes only the canary home, explicitly
    authorized project/dataset IDs, and its job-specific scratch.
11. Runtime cannot see `/mnt`, `/scitex-hub`, host root, Munge keys, Docker
    socket, or unrelated homes.
12. Removal/unavailability of the canary mount makes validation fail non-zero;
    no write lands in a local shadow `/scitex-hub` directory.
13. Remount and repeated validation are idempotent.
14. Existing SSHFS mounts and live Hub data are byte/path unchanged.

## Outage simulation

Do not interrupt NAS-02 globally. Exercise only the canary mount:

1. stop/unmount the canary unit;
2. confirm the owner-package runtime validator reports the missing exact mount
   source/type/mountpoint and `scitex-hub dev storage validate --json` exits
   non-zero; static dependency preflight is not sufficient;
3. confirm an unprivileged write to the unmounted service root is denied;
4. restore the mount;
5. confirm the canary file, owner, mode, and quota are unchanged;
6. confirm validation returns to green.

## Rollback

1. Stop new canary sessions.
2. Unmount `/scitex-hub` on compute-01.
3. Disable/remove only the new canary mount/automount unit.
4. Confirm the local mountpoint remains fail-closed and contains no shadow
   files.
5. Remove the canary-only client rule/export if it is separate from the future
   dedicated export.
6. Remove the canary resource/quota through the NAS-side provisioner.
7. Read back that existing SSHFS mounts, live Hub data, SLURM, and `/scratch`
   are unchanged.
8. Preserve the run manifest, logs, before/after measurements, and failure
   reason.

## Promotion gate

Do not add compute-02..04 or an external user until all acceptance probes pass,
rollback has been exercised, and the result is independently reviewed.
