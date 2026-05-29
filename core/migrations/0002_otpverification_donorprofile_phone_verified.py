# core/migrations/0002_otpverification_donorprofile_phone_verified.py
# Run:  python manage.py migrate

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        # Add phone_verified flag to DonorProfile
        migrations.AddField(
            model_name='donorprofile',
            name='phone_verified',
            field=models.BooleanField(default=False),
        ),
        # Create OTPVerification table
        migrations.CreateModel(
            name='OTPVerification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone', models.CharField(max_length=20)),
                ('code', models.CharField(max_length=6)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_used', models.BooleanField(default=False)),
            ],
        ),
    ]
