"""Every Hub-launched SLURM job carries a validated project + session tag."""

import uuid

import pytest

from apps.workspace.console_app.services.slurm.tags import (
    NO_PROJECT,
    SlurmTags,
    parse_comment,
    with_slurm_tags,
)

SESSION = "0f8fad5b-d9cb-469f-a165-70867728950e"


def test_comment_names_project_and_session():
    # Arrange
    tags = SlurmTags.for_project(42, session_id=SESSION)
    # Act
    comment = tags.comment
    # Assert
    assert comment == f"project:42,session:{SESSION}"


def test_wckey_is_p_prefixed_project_id():
    # Arrange
    tags = SlurmTags.for_project(42, session_id=SESSION)
    # Act
    wckey = tags.wckey
    # Assert
    assert wckey == "p42"


def test_no_project_is_tagged_explicitly_none():
    # Arrange
    tags = SlurmTags.for_project(NO_PROJECT, session_id=SESSION)
    # Act
    argv = tags.argv()
    # Assert
    assert argv == [f"--comment=project:none,session:{SESSION}", "--wckey=pnone"]


def test_no_project_has_no_project_id():
    # Arrange
    tags = SlurmTags.for_project(NO_PROJECT)
    # Act
    project_id = tags.project_id
    # Assert
    assert project_id is None


def test_none_is_not_accepted_as_no_project():
    # Arrange
    forgotten = None
    # Act
    # Assert
    with pytest.raises(ValueError):
        SlurmTags.for_project(forgotten)


def test_each_launch_gets_a_fresh_session():
    # Arrange
    first = SlurmTags.for_project(1)
    # Act
    second = SlurmTags.for_project(1)
    # Assert
    assert first.session_id != second.session_id


def test_directives_are_two_sbatch_lines():
    # Arrange
    tags = SlurmTags.for_project(9, session_id=SESSION)
    # Act
    lines = tags.directives().splitlines()
    # Assert
    assert lines == [
        f"#SBATCH --comment=project:9,session:{SESSION}",
        "#SBATCH --wckey=p9",
    ]


def test_with_slurm_tags_inserts_after_launcher():
    # Arrange
    tags = SlurmTags.for_project(9, session_id=SESSION)
    # Act
    argv = with_slurm_tags(["sbatch", "--parsable", "s.sh"], tags)
    # Assert
    assert argv[:3] == ["sbatch", *tags.argv()]


def test_with_slurm_tags_refuses_non_slurm_command():
    # Arrange
    tags = SlurmTags.for_project(9)
    # Act
    # Assert
    with pytest.raises(ValueError):
        with_slurm_tags(["bash", "-c", "true"], tags)


def test_parse_comment_round_trips():
    # Arrange
    tags = SlurmTags.for_project(9, session_id=SESSION)
    # Act
    parsed = parse_comment(tags.comment)
    # Assert
    assert parsed == {"project": "9", "session": SESSION}


def test_parse_comment_rejects_foreign_comment():
    # Arrange
    foreign = "nightly backup"
    # Act
    # Assert
    with pytest.raises(ValueError):
        parse_comment(foreign)


def test_uuid_object_session_is_canonicalised():
    # Arrange
    session = uuid.UUID(SESSION)
    # Act
    tags = SlurmTags.for_project(3, session_id=session)
    # Assert
    assert tags.session_id == SESSION


def test_record_uses_design_tag_names():
    # Arrange
    tags = SlurmTags.for_project(3, session_id=SESSION)
    # Act
    record = tags.as_record(user_id=5, workload="job")
    # Assert
    assert {
        "scitex.user": "5",
        "scitex.project": "3",
        "scitex.workload": "job",
        "scitex.session": SESSION,
    }.items() <= record.items()
