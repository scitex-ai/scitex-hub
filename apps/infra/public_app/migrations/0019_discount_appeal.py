# Academic appeal lane (operator CCT4558): the human-review queue for
# auto-check misses, plus the audit link from a grant back to its appeal.
# Hand-written in the shape `makemigrations` emits (cf. 0017/0018).

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('public_app', '0018_user_discount'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DiscountAppeal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('claimed_email', models.EmailField(max_length=254)),
                ('institution', models.CharField(max_length=200)),
                ('evidence', models.TextField(blank=True, default='', help_text='Staff page URL or affiliation note a reviewer can check.')),
                ('status', models.CharField(choices=[('open', 'Awaiting review'), ('approved', 'Approved — grant issued'), ('rejected', 'Rejected'), ('withdrawn', 'Withdrawn by requester')], default='open', max_length=16)),
                ('reviewer_note', models.TextField(blank=True, default='')),
                ('decided_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('decided_by', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='decided_discount_appeals', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='discount_appeals', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Discount Appeal',
                'verbose_name_plural': 'Discount Appeals',
                'ordering': ['-created_at'],
                'constraints': [models.UniqueConstraint(condition=models.Q(status='open'), fields=['user'], name='unique_open_discount_appeal_per_user')],
            },
        ),
        migrations.AddField(
            model_name='userdiscount',
            name='appeal',
            field=models.ForeignKey(blank=True, default=None, help_text='The approved appeal this grant was issued for, if any.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='grants', to='public_app.discountappeal'),
        ),
    ]
