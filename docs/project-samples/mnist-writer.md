# Explicit MNIST Writer showcase admission

`apps.infra.project_app.services.first_project_samples.mnist_writer` supplies
`plan_mnist_writer_demo(project_root)` and
`apply_mnist_writer_demo(project_root, expected_plan_sha256=...)`. These are
operator/service functions: the caller must authorize the exact existing project
root. They are not automatically invoked by a page GET, project selection or the
older `seed_first_project_samples()` helper.

The plan performs bounded reads only. It checks the existing claims/provenance
schemas and their numeric agreement, and verifies the provenance's exact SHA-256
identities for `claims.json` and `manuscript.pdf`. It accepts the documented
OpenML `mnist_784` v1/logistic-regression/kNN example, not arbitrary scientific
claims. Duplicate structured keys, malformed input, symlinks, hardlinked members,
nonregular/oversized members and changed-during-read identities are refused.

For Abstract, Methods and Results, replacement requires exact reviewed Writer
2.43.19 template bytes, or exact hashes recorded by an earlier successful seed.
A phrase such as “Replace this text” is never a replacement permission. Any
authored section or existing authored `SHOWCASE-MNIST.md` blocks the entire apply.
The returned `applicable`, per-section actions and `plan_sha256` allow review
before an explicitly requested apply. A stale plan is refused.

After authorization, an operator can use the normal configured Django shell:

```python
from apps.infra.project_app.models import Project
from apps.infra.project_app.services.filesystem.paths import get_project_root_path
from apps.infra.project_app.services.first_project_samples.mnist_writer import (
    plan_mnist_writer_demo, apply_mnist_writer_demo,
)

# Look up an existing project whose ownership the operator has already authorized.
project = Project.objects.get(pk=approved_project_id)
project_root = get_project_root_path(project.owner, project)
plan = plan_mnist_writer_demo(project_root)
# Inspect the plan before passing its exact reviewed hash to the explicit apply.
result = apply_mnist_writer_demo(
    project_root, expected_plan_sha256=reviewed_plan_sha256,
)
```

Do not run concurrent manuscript editors during this explicit apply. It reads through public `Writer(workspace).read_section()`, stages candidate bytes
through real `Writer.write_section()` in an owned temporary mini-workspace, and
preallocates same-directory publication/rollback files before replacing any project
section. It preserves each target file mode, explicitly refuses read-only sections,
and rechecks admitted target bytes/kernel identity immediately before replacement.
Each section publication is atomic; the whole batch is not a filesystem transaction.
It preserves immutable 0600 template originals under `.scitex/showcase/writer-mnist-v1-originals/`. If publication fails, it atomically restores earlier replacements only while
their bytes still exactly match this operation's published content; it preserves
concurrent author edits. Original backups remain available after a
failure. The deterministic admission record is
`.scitex/showcase/writer-mnist-v1.json`; repeat apply is byte/mtime idempotent.

The added `SHOWCASE-MNIST.md` explicitly distinguishes the existing computed
OpenML/logistic-regression/kNN artifact bundle from the project's untouched
Torch/UMAP/SVM template README/scripts. Neither the top-level README, bibliography,
scripts, other sections nor existing scientific artifacts are rewritten. The
manifest marks the claims as not independently verified. The content asserts no
significance test, confidence interval or publication status.

Seeding does not refresh/bootstrap an existing workspace, download data, train a
model or compile. In a separately authorized operation, the public compiler is
`scitex_writer.compile.manuscript(project_dir=str(workspace), ...)`. The existing
root Live Paper PDF is never copied into Writer compiler output. A screenshot of
a Writer PDF requires a genuine Writer compilation, not the seeding result alone.

## Evidence and tests

`tests/apps/project_app/services/test_mnist_writer_demo.py` uses actual Writer
2.43.19 section operations and an owned copy of the computed example. It covers
metric/output identity disagreement, authored-text preservation, stale plans,
symlink/FIFO/oversize refusal, backup preservation, explicit read-only refusal, actual file-size-limit failure inside staged Writer
writes without project truncation, separate showcase-note ownership, and repeat byte/mtime identity. No
network/domain service, existing project, compiler or model is invoked.

## Separate Writer API debt

The generic Writer `DocumentSection.write()` still uses direct `Path.write_text()`.
This coordinator does not change that public API or claim it is atomic; it hardens
only its own explicit demo publication. General Writer section-write atomicity is
a separate leaf-owned improvement.
