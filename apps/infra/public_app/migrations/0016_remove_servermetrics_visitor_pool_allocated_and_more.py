from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('public_app', '0015_plan_subscription'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='servermetrics',
            name='visitor_pool_allocated',
        ),
        migrations.RemoveField(
            model_name='servermetrics',
            name='visitor_pool_total',
        ),
    ]
