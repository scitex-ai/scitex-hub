# Folds spend_app.WorkloadSession into this model: one launch, one row.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("console_app", "0007_workloadsession"),
    ]

    operations = [
        migrations.AddField(
            model_name="workloadsession",
            name="cpus",
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="workloadsession",
            name="gpus",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="workloadsession",
            name="label",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
        migrations.AddField(
            model_name="workloadsession",
            name="max_seconds",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="workloadsession",
            name="memory_gb",
            field=models.PositiveSmallIntegerField(default=4),
        ),
        migrations.AddField(
            model_name="workloadsession",
            name="stop_reason",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Running (or stop not attributed)"),
                    ("completed", "Finished on its own"),
                    ("user", "Stopped by the user"),
                    ("idle", "Idle auto-stop"),
                    ("spend_cap", "Monthly spend cap reached"),
                    ("restricted", "Account restricted"),
                    ("expired", "Time limit reached"),
                    ("lost", "Ended without a stop record"),
                ],
                default="",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="workloadsession",
            name="scheduler",
            field=models.CharField(
                choices=[("slurm", "SLURM"), ("local", "Hub host process")],
                default="slurm",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="workloadsession",
            name="workload",
            field=models.CharField(
                choices=[
                    ("terminal", "Terminal"),
                    ("job", "Batch job"),
                    ("service", "Project service (notebook, TensorBoard, ...)"),
                ],
                max_length=20,
            ),
        ),
        migrations.AddIndex(
            model_name="workloadsession",
            index=models.Index(
                fields=["user", "stopped_at"], name="console_app_user_id_a4be5b_idx"
            ),
        ),
    ]
