from django.db import models
from django.contrib.auth.models import User


class ProfilUtilisateur(models.Model):
	utilisateur = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profil_kcomat')
	adresse = models.CharField(max_length=255, blank=True)
	telephone = models.CharField(max_length=30, blank=True)

	def __str__(self):
		return f"Profil {self.utilisateur.username}"
