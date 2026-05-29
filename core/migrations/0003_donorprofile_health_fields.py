from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_otpverification_donorprofile_phone_verified'),
    ]

    operations = [
        migrations.AddField(
            model_name='donorprofile',
            name='has_hiv',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='donorprofile',
            name='has_diabetes',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='donorprofile',
            name='has_sugar',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='donorprofile',
            name='has_skin_disease',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='donorprofile',
            name='covid_vaccinated',
            field=models.BooleanField(default=False),
        ),
    ]
