import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('public_app', '0014_payment_method'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PlanSubscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provider', models.CharField(default='stripe', max_length=32)),
                ('provider_subscription_id', models.CharField(max_length=255, unique=True)),
                ('provider_customer_id', models.CharField(blank=True, default='', max_length=255)),
                ('pricing_id', models.CharField(blank=True, default='', max_length=64)),
                ('status', models.CharField(default='incomplete', max_length=32)),
                ('cancel_at_period_end', models.BooleanField(default=False)),
                ('current_period_end', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='plan_subscriptions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Plan Subscription',
                'verbose_name_plural': 'Plan Subscriptions',
                'ordering': ['-created_at'],
            },
        ),
    ]
