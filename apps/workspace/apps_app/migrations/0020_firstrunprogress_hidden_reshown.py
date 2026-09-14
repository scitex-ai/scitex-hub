from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("apps_app", "0019_alter_appsmodule_visibility"),
    ]

    operations = [
        migrations.AddField(
            model_name="firstrunprogress",
            name="hidden_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="firstrunprogress",
            name="reshown_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
