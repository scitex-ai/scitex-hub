# Generated manually for visitor session auto-allocation feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('project_app', '0023_project_project_type_remotecredential_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='visitorallocation',
            name='last_activity',
            field=models.DateTimeField(
                blank=True,
                help_text='Last activity timestamp for idle detection',
                null=True
            ),
        ),
    ]
