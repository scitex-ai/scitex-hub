# Launch records now live in console_app.WorkloadSession (one launch, one
# row); console_app 0009 copied any rows here into it first.

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("spend_app", "0001_initial"),
        ("console_app", "0009_copy_spend_workloads"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="workloadsession",
            name="spend_app_w_user_id_cd122a_idx",
        ),
        migrations.RemoveIndex(
            model_name="workloadsession",
            name="spend_app_w_user_id_2c6d69_idx",
        ),
        migrations.DeleteModel(
            name="WorkloadSession",
        ),
    ]
