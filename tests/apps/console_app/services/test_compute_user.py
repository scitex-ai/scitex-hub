"""SLURM jobs are submitted as the hub user and see only that user's data."""

from apps.workspace.console_app.services.compute_user import (
    as_compute_user,
    compute_home,
    foreign_user_data_binds,
    instance_bind_sources,
    is_within,
    job_scratch_dir,
    provision_commands,
    with_sbatch_identity,
)
from apps.workspace.console_app.views.terminal._command_builder import (
    build_instance_start_script_cmd,
    build_sbatch_cmd,
)


def _sbatch(as_root=True):
    return build_sbatch_cmd(
        instance_name="scitex-alice",
        script_path="/app/data/.cache/alloc-scripts/s.sh",
        username="alice",
        project_slug="demo",
        uid=20001,
        gid=20001,
        as_root=as_root,
    )


def _instance_script(username="alice"):
    home = compute_home(username)
    return build_instance_start_script_cmd(
        container_path="/opt/scitex/singularity/current-sandbox",
        username=username,
        host_user_dir=home,
        host_project_dir=home / "proj" / "demo",
        project_slug="demo",
        instance_name=f"scitex-{username}",
        scratch_dir=job_scratch_dir(username, "0123abcd-ffff"),
    )


class TestSbatchArgv:
    def test_root_broker_passes_uid_and_gid(self):
        # Arrange
        expected = {"--uid=20001", "--gid=20001"}
        # Act
        argv = _sbatch(as_root=True)
        # Assert
        assert expected <= set(argv)

    def test_targets_the_compute_partition(self):
        # Arrange
        expected = "--partition=compute"
        # Act
        argv = _sbatch()
        # Assert
        assert expected in argv

    def test_non_root_broker_omits_uid(self):
        # Arrange
        cmd = ["sbatch", "--parsable", "job.sh"]
        # Act
        argv = with_sbatch_identity(cmd, 20001, 20001, as_root=False)
        # Assert
        assert argv == cmd

    def test_identity_flags_follow_sbatch_directly(self):
        # Arrange
        cmd = ["sbatch", "--parsable", "job.sh"]
        # Act
        argv = with_sbatch_identity(cmd, 20001, 20002, as_root=True)
        # Assert
        assert argv[:3] == ["sbatch", "--uid=20001", "--gid=20002"]


class TestInstanceBinds:
    def test_only_the_users_home_and_job_scratch_are_bound(self):
        # Arrange
        home = compute_home("alice")
        scratch = str(job_scratch_dir("alice", "0123abcd-ffff"))
        # Act
        outside_home = {
            src
            for src in instance_bind_sources(_instance_script("alice"))
            if not is_within(src, home)
        }
        # Assert
        assert outside_home == {scratch}

    def test_home_bind_is_under_storage_cool_users(self):
        # Arrange
        script = _instance_script("alice")
        # Act
        sources = instance_bind_sources(script)
        # Assert
        assert "/storage/cool/users/alice" in sources

    def test_another_users_home_is_flagged(self):
        # Arrange
        script = (
            "apptainer instance start --home /storage/cool/users/alice:/home/alice "
            "--bind /storage/cool/users/bob/proj/x:/home/alice/proj/x:rw img inst"
        )
        # Act
        foreign = foreign_user_data_binds(script, "alice")
        # Assert
        assert foreign == ["/storage/cool/users/bob/proj/x"]

    def test_scratch_is_created_private_before_the_instance(self):
        # Arrange
        script = _instance_script("alice")
        # Act
        mkdir_at = script.find("mkdir -m 700")
        # Assert
        assert 0 <= mkdir_at < script.find("apptainer instance start")


class TestShellDrop:
    def test_shell_runs_as_user_inside_srun_step(self):
        # Arrange
        cmd = ["srun", "--pty", "--overlap", "--jobid=7", "apptainer", "exec", "x"]
        # Act
        argv = as_compute_user(cmd, 20001, 20001)
        # Assert
        assert argv[4:8] == [
            "setpriv",
            "--reuid=20001",
            "--regid=20001",
            "--clear-groups",
        ]


class TestProvisionCommands:
    def test_one_useradd_per_node_plus_controller_setup(self):
        # Arrange
        nodes = ["compute-01", "compute-02", "compute-03", "compute-04"]
        # Act
        cmds = provision_commands("alice", 20001, 20001, nodes)
        # Assert
        assert [c[1] for c in cmds] == [*nodes, "compute-01"]

    def test_useradd_uses_the_allocated_uid(self):
        # Arrange
        nodes = ["compute-02"]
        # Act
        node_script = provision_commands("alice", 20007, 20007, nodes)[0][2]
        # Assert
        assert "useradd -u 20007 -g 20007" in node_script

    def test_slurm_association_uses_the_scitex_account(self):
        # Arrange
        nodes = ["compute-01"]
        # Act
        controller_script = provision_commands("alice", 20001, 20001, nodes)[-1][2]
        # Assert
        assert "sacctmgr -i add user alice DefaultAccount=scitex" in controller_script
