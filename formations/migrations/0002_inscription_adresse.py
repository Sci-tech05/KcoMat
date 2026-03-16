from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('formations', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='inscription',
            name='adresse',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
