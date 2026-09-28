# Stage-1 pytest shard planner

Stage 1 adds an offline planner and its contract tests. It does **not** change
which required jobs run, their names, or their resource limits.

## Required CI remains unchanged

`.github/workflows/pytest-matrix-on-ubuntu-py3-11-3-12-3-13.yml` still runs the
full `tests/` tree in each required context:

- `pytest-matrix-on-ubuntu-py3.11`
- `pytest-matrix-on-ubuntu-py3.12`
- `pytest-matrix-on-ubuntu-py3.13`

The self-hosted job container remains capped at `--cpus 8`, and xdist remains
explicitly bounded to 8 workers in that container (`auto` only on the bounded
GitHub-hosted VM). The required workflow does not call the new planner.

No canary workflow is added in Stage 1. There is no measured spare-runner
capacity proving that another matrix or shard job can run without contending
with the three required jobs. Adding one would therefore risk oversubscription
rather than provide safe evidence.

## Planner contract

`scripts/ci/pytest_shards.py` discovers `test_*.py` files, estimates each file's
weight from its test definitions, and applies deterministic largest-first
greedy balancing. Paths and equal-weight bundles use lexical tie-breakers, and
shard-index tie-breaking is stable.

Cross-file serialization is generic and opt-in. One logical group may contain
one or more repository-relative directories by repeating its name:

```bash
python scripts/ci/pytest_shards.py \
  --repo-root . \
  --test-root tests \
  --shards 3 \
  --serial-group shared-state=tests/integration/writer_state \
  --serial-group shared-state=tests/integration/reader_state
```

Every file under either declared directory becomes one indivisible bundle. No
product-specific group is compiled into the planner, and the default group set
is empty. A future caller must declare every active cross-file shared-state
contract explicitly.

The command builds and validates the complete plan before writing JSON. It
fails nonzero and emits no partial manifest when:

- discovery selects no tests;
- a requested shard would be empty;
- a declared group or any of its directories selects no files;
- group declarations overlap, duplicate a directory, or use unsafe paths;
- input contains duplicate files;
- a file-weight read/helper fails; or
- final coverage differs from the input (missing or duplicate files).

## Active serialization audit

The audit found no active cross-file serialization contract to promote into the
planner. Legacy compatibility grouping remains untouched so Stage 1 does not
alter required-job execution, but it is not copied into new sharding
configuration. The planner therefore has no default serial groups; future
callers must declare and test only the active shared-state contracts that exist
at migration time.

## Before a required-job migration

A later stage must separately prove all of the following before switching any
required context:

1. every then-active shared-state group is declared and tested as atomic;
2. manifests cover the collected test files exactly once;
3. per-shard worker counts and container CPU limits are explicit and do not
   increase aggregate host concurrency;
4. Python 3.11, 3.12, and 3.13 all still execute the full suite; and
5. the three existing required context names remain unchanged.
