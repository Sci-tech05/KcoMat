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
            name='ProfilUtilisateur',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('adresse', models.CharField(blank=True, max_length=255)),
                ('telephone', models.CharField(blank=True, max_length=30)),
                ('utilisateur', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profil_kcomat', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
