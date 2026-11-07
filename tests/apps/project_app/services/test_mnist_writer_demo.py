"""Real Writer section operations, using only an owned copy of the computed demo."""

import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest
import yaml

from apps.infra.project_app.services.first_project_samples._mnist_facts import (
    DemoSeedRefused,
)
from apps.infra.project_app.services.first_project_samples.mnist_writer import (
    BACKUP_RELPATH,
    SECTIONS,
    STATE_RELPATH,
    TEMPLATE_ROOT,
    WRITER_WORKSPACE_RELPATH,
    apply_mnist_writer_demo,
    plan_mnist_writer_demo,
)

FIXTURE = Path(__file__).with_name("_fixtures") / "mnist_writer"


def snapshot(root):
    return {
        str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()
    }


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "demo"
    shutil.copytree(FIXTURE, root)
    workspace = root / WRITER_WORKSPACE_RELPATH
    for part in (
        "00_shared",
        "01_manuscript/contents",
        "02_supplementary",
        "03_revision",
        "scripts",
    ):
        (workspace / part).mkdir(parents=True, exist_ok=True)
    for name in SECTIONS:
        shutil.copyfile(
            TEMPLATE_ROOT / f"{name}.tex",
            workspace / f"01_manuscript/contents/{name}.tex",
        )
    (workspace / "00_shared/bibliography.bib").write_text(
        "Authored bibliography: preserved.\n"
    )
    (workspace / "scripts/owned.sh").write_text("Authored script: preserved.\n")
    return root


def section(root, name):
    return root / WRITER_WORKSPACE_RELPATH / f"01_manuscript/contents/{name}.tex"


def apply(root):
    plan = plan_mnist_writer_demo(root)
    return apply_mnist_writer_demo(root, expected_plan_sha256=plan["plan_sha256"])


def test_plan_is_deterministic_and_has_no_filesystem_side_effects(project):
    before = snapshot(project)
    first = plan_mnist_writer_demo(project)
    second = plan_mnist_writer_demo(project)
    assert first == second and first["applicable"]
    assert [r["action"] for r in first["sections"]] == ["seed"] * 3
    assert snapshot(project) == before
    assert not (project / ".scitex/showcase").exists()


def test_real_writer_applies_derived_example_sections_and_preserves_other_members(
    project,
):
    before = snapshot(project)
    result = apply(project)
    assert result["changed"] == list(SECTIONS)
    assert "0.8825" in section(project, "abstract").read_text()
    assert "0.8910" in section(project, "results").read_text()
    assert "-0.0085" in section(project, "results").read_text()
    assert "10,000" in section(project, "methods").read_text()
    assert "2,000" in section(project, "methods").read_text()
    assert "not a research finding" in section(project, "abstract").read_text()
    for path, data in before.items():
        if not any(path.endswith(f"/contents/{name}.tex") for name in SECTIONS):
            assert (project / path).read_bytes() == data
    for name in SECTIONS:
        backup = project / BACKUP_RELPATH / f"{name}.tex"
        assert backup.read_bytes() == (TEMPLATE_ROOT / f"{name}.tex").read_bytes()
        assert backup.stat().st_mode & 0o777 == 0o600
    assert (project / STATE_RELPATH).stat().st_mode & 0o777 == 0o600


def test_repeated_apply_is_byte_and_mtime_idempotent(project):
    apply(project)
    before = snapshot(project)
    mtimes = {str(p): p.stat().st_mtime_ns for p in project.rglob("*") if p.is_file()}
    result = apply(project)
    assert result["changed"] == []
    assert snapshot(project) == before
    assert {
        str(p): p.stat().st_mtime_ns for p in project.rglob("*") if p.is_file()
    } == mtimes


def test_authored_text_containing_old_placeholder_phrase_is_never_replaced(project):
    section(project, "abstract").write_text(
        "Authored: Replace this text is discussed here.\n"
    )
    before = snapshot(project)
    plan = plan_mnist_writer_demo(project)
    assert not plan["applicable"]
    assert plan["sections"][0]["action"] == "preserve-authored"
    with pytest.raises(DemoSeedRefused, match="authored"):
        apply_mnist_writer_demo(project, expected_plan_sha256=plan["plan_sha256"])
    assert snapshot(project) == before


def test_stale_plan_cannot_overwrite_a_new_author_edit(project):
    plan = plan_mnist_writer_demo(project)
    section(project, "results").write_text("New authored result.\n")
    before = snapshot(project)
    with pytest.raises(DemoSeedRefused, match="reviewed plan"):
        apply_mnist_writer_demo(project, expected_plan_sha256=plan["plan_sha256"])
    assert snapshot(project) == before


def test_editing_a_previous_seed_revokes_replacement_admission(project):
    apply(project)
    section(project, "methods").write_text(
        "Edited by the author after demo admission.\n"
    )
    before = snapshot(project)
    with pytest.raises(DemoSeedRefused, match="authored"):
        apply(project)
    assert snapshot(project) == before


@pytest.mark.parametrize("member", ["claims.json", "manuscript.pdf"])
def test_output_hash_disagreement_refuses_without_changing_sections(project, member):
    path = project / member
    path.write_bytes(path.read_bytes() + b"\n")
    before = snapshot(project)
    with pytest.raises(DemoSeedRefused, match="output bytes"):
        plan_mnist_writer_demo(project)
    assert snapshot(project) == before


def test_claim_metric_disagreement_is_detected_even_with_consistent_output_hash(
    project,
):
    path = project / "claims.json"
    claims = json.loads(path.read_text())
    claims["claims"][0]["claim_value"] = "logistic regression test accuracy = 0.9000"
    path.write_text(json.dumps(claims))
    provenance = yaml.safe_load((project / "provenance.yaml").read_text())
    for row in provenance["sessions"]["sess_train"]["outputs"]:
        if row["path"] == "claims.json":
            row["hash"] = hashlib.sha256(path.read_bytes()).hexdigest()
    (project / "provenance.yaml").write_text(yaml.safe_dump(provenance))
    with pytest.raises(DemoSeedRefused, match="result values"):
        plan_mnist_writer_demo(project)


@pytest.mark.parametrize(
    "member",
    [
        "claims.json",
        "provenance.yaml",
        "manuscript.pdf",
        f"{WRITER_WORKSPACE_RELPATH}/01_manuscript/contents/abstract.tex",
    ],
)
def test_symlink_members_are_refused(project, tmp_path, member):
    path = project / member
    foreign = tmp_path / "outside"
    foreign.write_bytes(path.read_bytes())
    path.unlink()
    path.symlink_to(foreign)
    with pytest.raises(DemoSeedRefused, match="Symbolic"):
        plan_mnist_writer_demo(project)
    assert foreign.read_bytes() == path.read_bytes()


def test_workspace_symlink_is_not_an_authorized_subtree(project, tmp_path):
    workspace = project / WRITER_WORKSPACE_RELPATH
    moved = tmp_path / "outside-workspace"
    workspace.rename(moved)
    workspace.symlink_to(moved, target_is_directory=True)
    with pytest.raises(DemoSeedRefused, match="Symbolic"):
        plan_mnist_writer_demo(project)


def test_missing_section_is_not_treated_as_an_empty_template(project):
    section(project, "abstract").unlink()
    with pytest.raises(DemoSeedRefused, match="absent"):
        plan_mnist_writer_demo(project)


def test_oversized_input_is_refused_before_parsing(project):
    (project / "claims.json").write_bytes(b"x" * 65537)
    with pytest.raises(DemoSeedRefused, match="bounded"):
        plan_mnist_writer_demo(project)


def test_fifo_is_promptly_refused_without_reading_it(project):
    path = project / "claims.json"
    path.unlink()
    os.mkfifo(path)
    with pytest.raises(DemoSeedRefused, match="regular"):
        plan_mnist_writer_demo(project)


def test_previous_original_backup_tampering_is_not_silently_accepted(project):
    apply(project)
    (project / BACKUP_RELPATH / "abstract.tex").write_text("Different original.\n")
    with pytest.raises(DemoSeedRefused, match="backup differs"):
        plan_mnist_writer_demo(project)


def test_existing_backup_collision_stops_before_any_section_write(project):
    backup = project / BACKUP_RELPATH / "abstract.tex"
    backup.parent.mkdir(parents=True)
    backup.write_text("User file: do not overwrite.\n")
    before = snapshot(project)
    with pytest.raises(DemoSeedRefused, match="backup must never"):
        apply(project)
    assert snapshot(project) == before


def test_explicit_read_only_section_is_refused_before_publication(project):
    before = {name: section(project, name).read_bytes() for name in SECTIONS}
    target = section(project, "methods")
    target.chmod(0o400)
    try:
        with pytest.raises(DemoSeedRefused, match="Writer refused"):
            apply(project)
    finally:
        target.chmod(0o600)
    assert {name: section(project, name).read_bytes() for name in SECTIONS} == before
    assert not (project / STATE_RELPATH).exists()
    assert (project / BACKUP_RELPATH / "abstract.tex").exists()


def test_showcase_note_separates_computed_bundle_from_preserved_template_readme(
    project,
):
    readme = project / "README.md"
    readme.write_text("Authored template: Torch/UMAP/SVM; do not rewrite.\n")
    result = apply(project)
    note = (project / "SHOWCASE-MNIST.md").read_text()
    assert result["showcase_note_changed"]
    assert "separate Torch/UMAP/SVM" in note
    assert "OpenML/logistic-regression/kNN metrics" in note
    assert "never copied into Writer compiler output" in note
    assert "0.8825" in note and "0.8910" in note
    assert readme.read_text() == "Authored template: Torch/UMAP/SVM; do not rewrite.\n"
    state = json.loads((project / STATE_RELPATH).read_text())
    assert state["independently_verified"] is False
    assert state["showcase_note_sha256"] == hashlib.sha256(note.encode()).hexdigest()


def test_preexisting_authored_showcase_note_blocks_all_writes(project):
    (project / "SHOWCASE-MNIST.md").write_text("My own showcase explanation.\n")
    before = snapshot(project)
    assert not plan_mnist_writer_demo(project)["applicable"]
    with pytest.raises(DemoSeedRefused, match="authored"):
        apply(project)
    assert snapshot(project) == before


def test_authored_edit_to_previous_showcase_note_blocks_reseed(project):
    apply(project)
    (project / "SHOWCASE-MNIST.md").write_text("Authored explanation after seed.\n")
    before = snapshot(project)
    with pytest.raises(DemoSeedRefused, match="authored"):
        apply(project)
    assert snapshot(project) == before


@pytest.mark.parametrize(
    "member,content",
    [
        ("claims.json", '{"schema":"one","schema":"two"}'),
        ("provenance.yaml", "schema: one\nschema: two\n"),
    ],
)
def test_duplicate_input_keys_are_not_silently_reinterpreted(project, member, content):
    (project / member).write_text(content)
    with pytest.raises(DemoSeedRefused, match="Duplicate"):
        plan_mnist_writer_demo(project)


@pytest.mark.parametrize("tag", ["!!python/object/apply:os.system", "!!python/object/new:os.system"])
def test_python_yaml_constructors_are_refused_without_execution(project, tmp_path, tag):
    marker = tmp_path / "must-not-exist"
    (project / "provenance.yaml").write_text(f"{tag} ['touch {marker}']\n")
    before = snapshot(project)
    try:
        with pytest.raises(DemoSeedRefused, match="malformed"):
            plan_mnist_writer_demo(project)
    finally:
        assert not marker.exists()
        assert snapshot(project) == before


def test_malformed_yaml_fails_with_typed_refusal(project):
    (project / "provenance.yaml").write_text("schema: [unterminated")
    with pytest.raises(DemoSeedRefused, match="malformed"):
        plan_mnist_writer_demo(project)


@pytest.mark.parametrize("limit,phase", [(300, "staged"), (512, "note")])
def test_real_file_size_failure_never_truncates_project_sections(project, limit, phase):
    import subprocess
    import sys

    source_root = Path(__file__).resolve().parents[4]
    before = {name: section(project, name).read_bytes() for name in SECTIONS}
    code = r"""
import os,resource,signal,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
os.environ.pop('DJANGO_SETTINGS_MODULE',None)
os.environ['SCITEX_STORE_DSN']='postgresql://unavailable@127.0.0.1:1/owned_test_unavailable?connect_timeout=1'
from django.conf import settings
settings.configure(SECRET_KEY='owned-file-size-test',INSTALLED_APPS=['django.contrib.auth','django.contrib.contenttypes','apps.infra.project_app','apps.infra.organizations_app'],DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':':memory:'}},BASE_DIR=Path(sys.argv[1]),USE_I18N=False)
import django;django.setup()
from apps.infra.project_app.services.first_project_samples.mnist_writer import plan_mnist_writer_demo,apply_mnist_writer_demo,DemoSeedRefused
root=Path(sys.argv[2]);plan=plan_mnist_writer_demo(root)
# Resolve actual lazy Writer/IO imports before limiting only the operation.
from scitex_writer import Writer
from apps.infra.project_app.services.writer_workspace_layout import WRITER_WORKSPACE_RELPATH
writer=Writer(root/WRITER_WORKSPACE_RELPATH,git_strategy=None)
for name in ('abstract','methods','results'): writer.read_section(name)
original_limits=resource.getrlimit(resource.RLIMIT_FSIZE)
original_signal=signal.getsignal(signal.SIGXFSZ)
signal.signal(signal.SIGXFSZ,signal.SIG_IGN)
limit=int(sys.argv[3]);phase=sys.argv[4]
resource.setrlimit(resource.RLIMIT_FSIZE,(limit,original_limits[1]))
try:
 apply_mnist_writer_demo(root,expected_plan_sha256=plan['plan_sha256'])
except (DemoSeedRefused,OSError) as error:
 if phase=='staged':
  assert isinstance(error,DemoSeedRefused) and 'staged section write' in str(error),type(error).__name__
 else:
  assert isinstance(error,OSError) and error.errno==27,type(error).__name__
 print('actual-file-size-refusal-'+phase)
else:
 raise AssertionError('The actual staged Writer write must exceed the file-size limit')
finally:
 resource.setrlimit(resource.RLIMIT_FSIZE,original_limits)
 signal.signal(signal.SIGXFSZ,original_signal)
assert resource.getrlimit(resource.RLIMIT_FSIZE)==original_limits
"""
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            code,
            str(source_root),
            str(project),
            str(limit),
            phase,
        ],
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "actual-file-size-refusal-" + phase in result.stdout
    assert {name: section(project, name).read_bytes() for name in SECTIONS} == before
    assert not (project / STATE_RELPATH).exists()
    assert not (project / "SHOWCASE-MNIST.md").exists()
    assert not list((project / WRITER_WORKSPACE_RELPATH).rglob(".mnist-section-*"))


def test_seed_preserves_existing_section_modes(project):
    for name in SECTIONS:
        section(project, name).chmod(0o640)
    apply(project)
    assert [section(project, name).stat().st_mode & 0o777 for name in SECTIONS] == [
        0o640
    ] * 3


def test_hardlinked_input_is_not_an_owned_regular_artifact(project, tmp_path):
    os.link(project / "claims.json", tmp_path / "second-link")
    with pytest.raises(DemoSeedRefused, match="singly linked"):
        plan_mnist_writer_demo(project)


def _prepared_context(project):
    from apps.infra.project_app.services.first_project_samples._mnist_commit import (
        stage_sections,
    )
    from apps.infra.project_app.services.first_project_samples._mnist_facts import (
        load_facts,
        section_text,
    )

    plan = plan_mnist_writer_demo(project)
    facts, _ = load_facts(project)
    text = section_text(facts)
    originals = {name: section(project, name).read_bytes() for name in SECTIONS}

    def relative(name):
        return section(project, name).relative_to(project)

    return (
        stage_sections(project, plan["sections"], originals, text, relative),
        plan,
        text,
    )


def test_atomic_publish_refuses_same_bytes_with_a_changed_kernel_file_identity(project):
    from apps.infra.project_app.services.first_project_samples._mnist_commit import (
        publish_section,
    )

    context, plan, _ = _prepared_context(project)
    with context as prepared:
        target = section(project, "abstract")
        replacement = target.with_name("replacement.tex")
        replacement.write_bytes(target.read_bytes())
        os.replace(replacement, target)
        with pytest.raises(DemoSeedRefused, match="identity changed"):
            publish_section(
                project,
                target.relative_to(project),
                plan["sections"][0]["before_sha256"],
                prepared["abstract"],
            )


@pytest.mark.parametrize("edit", ["content", "mode"])
def test_atomic_rollback_preserves_concurrent_author_change(project, edit):
    from apps.infra.project_app.services.first_project_samples._mnist_commit import (
        publish_section,
        restore_section_if_ours,
    )

    context, plan, text = _prepared_context(project)
    with context as prepared:
        target = section(project, "abstract")
        relative = target.relative_to(project)
        publish_section(
            project,
            relative,
            plan["sections"][0]["before_sha256"],
            prepared["abstract"],
        )
        if edit == "content":
            target.write_text("Concurrent authored content.\n")
        else:
            target.chmod(0o400)
        restore_section_if_ours(
            project,
            relative,
            hashlib.sha256(text["abstract"].encode()).hexdigest(),
            prepared["abstract"],
        )
        if edit == "content":
            assert target.read_text() == "Concurrent authored content.\n"
        else:
            assert target.stat().st_mode & 0o777 == 0o400
            assert target.read_text() == text["abstract"]
