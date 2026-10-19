# Academic discount lane (operator CCT4555): the 1:1 user→discount mapping.
# Hand-written in the shape `makemigrations` emits (cf. 0017): one new model,
# no data migration — eligibility is granted at verification from here on,
# and pre-lane accounts earn their row the next time they verify an address.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('public_app', '0017_billing_processing_and_setup_session'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserDiscount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(default='ACADEMIC50', max_length=32)),
                ('status', models.CharField(choices=[('active', 'Discount applies'), ('revoked', 'Revoked by an administrator')], default='active', max_length=16)),
                ('verified_email', models.EmailField(max_length=254)),
                ('basis_domain', models.CharField(blank=True, default='', max_length=253)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='discount', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'User Discount',
                'verbose_name_plural': 'User Discounts',
            },
        ),
    ]
