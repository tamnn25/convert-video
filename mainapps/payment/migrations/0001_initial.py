# Generated by Django 3.2.25 on 2024-10-13 06:30

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserSubscription',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('COMPLETED', 'COMPLETED'), ('INACTIVE', 'INACTIVE'), ('ACTIVE', 'ACTIVE'), ('CANCELED', 'CANCELED'), ('TRIAL', 'TRIAL')], max_length=20)),
                ('expiration_at', models.DateTimeField()),
                ('subscription_id', models.CharField(max_length=36)),
                ('subscription_type', models.CharField(max_length=20)),
                ('name', models.CharField(max_length=100)),
                ('payment_info', models.TextField(blank=True, null=True)),
                ('amount_allowed_usage', models.IntegerField()),
                ('amount_used_usage', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subscriptions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'User Subscription',
                'verbose_name_plural': 'User Subscriptions',
                'db_table': 'user_subscriptions',
            },
        ),
    ]
