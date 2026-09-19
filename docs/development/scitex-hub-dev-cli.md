# `scitex-hub dev`: operator/developer entry point

`scitex-hub dev` is the task-oriented place to discover how to set up,
audit, validate, and maintain SciTeX Hub. It is an orchestration facade, not
the owner of every implementation.

## Responsibility map

| Hub command area | Owning package | Responsibility |
|---|---|---|
| `dev storage` | `scitex-storage` | Storage measurement, Broker contract, quota/provisioning primitives |
| `dev resource` | `scitex-resource` | Host specs and CPU/RAM/GPU/load context |
| `dev slurm` | `scitex-hpc` | SLURM dispatch, accounting, QoS/limit evidence |
| `dev ssh` | `scitex-ssh` | Remote probe/transport and SSH policy evidence |
| `dev container` | `scitex-container` | Apptainer isolation and authorized runtime binds |
| `dev identity` | Hub policy | One stable `ComputeIdentity` UID/GID contract |
| `dev setup` | Hub orchestration | Ordered plan across the owning packages |
| `dev maintenance` | Hub orchestration | Discover backup/restore/repair/rotation entry points |

Hub must not duplicate leaf behavior. A `dev` command should call a public
Python API from the owner package where one exists, and report the delegated
package/version in structured output.

## Current Stage-0 commands

```bash
scitex-hub dev --help
scitex-hub dev doctor --json
scitex-hub dev setup plan --json

scitex-hub dev storage audit --json
scitex-hub dev storage validate --json
scitex-hub dev storage canary plan --json

scitex-hub dev identity validate --json
scitex-hub dev resource validate --json
scitex-hub dev slurm validate --json
scitex-hub dev ssh validate --json
scitex-hub dev container validate --json
```

All current commands are read-only. `validate` exits non-zero when the target
contract is not satisfied. `audit` reports the observed state without failing
only because rollout is incomplete.

`setup plan` is deliberately non-mutating. `apply` and `rollback` are not
exposed until the typed Storage Broker and split NAS/node executors exist.

## Safety contract

- `dev` is operator/developer-only and is never part of the customer SSH
  allowlist.
- No command accepts a generic shell string, raw `argv`, or an unvalidated
  filesystem path for privileged execution.
- Mutating commands must follow `plan -> apply -> validate -> rollback`, carry
  an idempotency key, and read back exact postconditions before success.
- Hub Web never receives a general NAS administrator credential or a generic
  root-execution API.
- Customer interactive UX remains commandless `ssh user@host`; a future
  `scitex-hub shell` may be a convenience alias but is not required for MVP.

## Initial setup order

1. `doctor`
2. storage
3. identity
4. resource context
5. SSH
6. SLURM
7. container runtime
8. single-node canary

The target architecture and acceptance criteria are documented in
`SciTeX_Hub_Login_Storage_Design_v3.2_2026-09-16.pdf` (operator artifact).
