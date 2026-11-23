import re
import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from core.relances import RelancePaiementMixin

# Calendrier d'une séance (par rapport à date_debut / date_fin)
RAPPEL_AVANT = timedelta(minutes=20)        # notification push + e-mail aux inscrits
OUVERTURE_SALLE = timedelta(minutes=10)     # le bouton « Participer » apparaît
PROLONGATION_SALLE = timedelta(minutes=30)  # la salle reste ouverte si la séance déborde

YOUTUBE_ID = re.compile(r'[A-Za-z0-9_-]{11}')
YOUTUBE_LIEN = re.compile(r'(?:youtube(?:-nocookie)?\.com/(?:watch\?(?:.*&)?v=|live/|embed/|shorts/)|youtu\.be/)'
                          r'([A-Za-z0-9_-]{11})')

# Thème : libellé, icône (partials/icon.html), dégradé de la couverture
THEMES = {
    'embarque': ('Systèmes embarqués', 'cpu', '#0A84FF', '#22D3EE'),
    'iot': ('IoT & Cloud', 'wifi', '#06B6D4', '#10B981'),
    'ia': ('Edge AI', 'sparkles', '#8B5CF6', '#EC4899'),
    'python': ('Python & automatisation', 'code', '#2563EB', '#FACC15'),
    'algorithmique': ('Algorithmique & programmation', 'network', '#0EA5E9', '#6366F1'),
    'domotique': ('Domotique', 'home', '#10B981', '#84CC16'),
    'entrepreneuriat': ('Entrepreneuriat tech', 'lightbulb', '#F97316', '#F43F5E'),
    'robotique': ('Robotique', 'bot', '#6366F1', '#22D3EE'),
    'autre': ('Technologie', 'radio', '#0A84FF', '#8B5CF6'),
}


class WebinaireQuerySet(models.QuerySet):
    def publies(self):
        return self.filter(actif=True)

    def a_venir(self, maintenant=None):
        """Publiés et pas encore terminés (en cours compris), du plus proche au plus lointain."""
        return self.publies().filter(date_fin__gt=maintenant or timezone.now()).order_by('date_debut')

    def passes(self, maintenant=None):
        return self.publies().filter(date_fin__lte=maintenant or timezone.now()).order_by('-date_debut')


class Webinaire(models.Model):
    THEME_CHOICES = [(cle, valeurs[0]) for cle, valeurs in THEMES.items()]

    titre = models.CharField("Titre / sujet", max_length=160)
    slug = models.SlugField(unique=True, blank=True, max_length=180)
    theme = models.CharField("Thème", max_length=20, choices=THEME_CHOICES, default='embarque',
                             help_text="Donne l'icône et les couleurs de la carte (et de la couverture si aucune image).")
    accroche = models.CharField("Accroche", max_length=220,
                                help_text="Une ou deux phrases affichées sur les cartes et dans la notification.")
    description = models.TextField(help_text="Présentation complète du webinaire. Une ligne vide sépare les paragraphes.")
    points_cles = models.TextField("Ce que vous allez apprendre", blank=True, help_text="Un point par ligne.")
    image = models.ImageField(upload_to='webinaires/', blank=True, null=True,
                              help_text="Format paysage conseillé (1600 × 900 px). Sans image, une couverture aux couleurs du thème est affichée.")
    intervenant = models.CharField("Intervenant", max_length=120, default="Équipe pédagogique KcoMat")
    intervenant_fonction = models.CharField("Fonction de l'intervenant", max_length=160, blank=True,
                                            default="Formateurs en électronique, IoT et IA")
    date_debut = models.DateTimeField("Début")
    date_fin = models.DateTimeField("Fin")
    places = models.PositiveIntegerField("Places", default=0, help_text="0 = places illimitées.")
    prix_attestation = models.PositiveIntegerField(
        "Prix de l'attestation (FCFA)", default=0,
        help_text="0 = attestation gratuite. Sinon, la participation reste gratuite mais l'attestation ne se "
                  "télécharge qu'après paiement en ligne de ce montant.")
    actif = models.BooleanField("Publié", default=False,
                                help_text="Publier envoie aussitôt une notification aux abonnés du site.")
    youtube_direct = models.CharField(
        "Direct YouTube", max_length=200, blank=True,
        help_text="Lien du direct YouTube (youtube.com/live/…, youtu.be/…, watch?v=…). Renseigné, il est diffusé dans la "
                  "salle du site pour tous les inscrits, sans limite de nombre ; la visio Jitsi reste réservée à "
                  "l'animation et aux personnes qui veulent prendre la parole.")
    salle_jitsi = models.CharField("Salle de visioconférence", max_length=120, blank=True, editable=False)
    rappel_envoye_le = models.DateTimeField("Rappel envoyé le", null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = WebinaireQuerySet.as_manager()

    class Meta:
        ordering = ['-date_debut']
        verbose_name = "Webinaire"
        verbose_name_plural = "Webinaires"

    def __str__(self):
        return self.titre

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.titre)[:150] or 'webinaire'
            slug, n = base, 2
            while Webinaire.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        if not self.salle_jitsi:
            self.salle_jitsi = f"kcomat-webinaire-{slugify(self.titre)[:40] or 'live'}-{uuid.uuid4().hex[:8]}"
        super().save(*args, **kwargs)

    def clean(self):
        if self.date_debut and self.date_fin and self.date_fin <= self.date_debut:
            raise ValidationError({'date_fin': "La fin doit être postérieure au début."})
        if self.youtube_direct and not self.youtube_id:
            raise ValidationError({'youtube_direct': "Lien YouTube non reconnu : copiez l'adresse du direct "
                                                     "(par exemple https://youtube.com/live/XXXXXXXXXXX)."})

    def get_absolute_url(self):
        return reverse('webinaires:detail', args=[self.slug])

    # ------------------------------------------------------------------ calendrier
    @property
    def ouverture_salle(self):
        return self.date_debut - OUVERTURE_SALLE

    @property
    def heure_rappel(self):
        return self.date_debut - RAPPEL_AVANT

    def statut(self, maintenant=None):
        """a_venir → ouvert (salle ouverte, 10 min avant) → en_direct → termine."""
        maintenant = maintenant or timezone.now()
        if maintenant >= self.date_fin:
            return 'termine'
        if maintenant >= self.date_debut:
            return 'en_direct'
        if maintenant >= self.ouverture_salle:
            return 'ouvert'
        return 'a_venir'

    def salle_ouverte(self, maintenant=None):
        maintenant = maintenant or timezone.now()
        return self.ouverture_salle <= maintenant < self.date_fin + PROLONGATION_SALLE

    @property
    def est_cloturee(self):
        # lu par notifications.signals : pas d'annonce pour une séance déjà passée
        return timezone.now() >= self.date_fin

    @property
    def duree(self):
        minutes = int((self.date_fin - self.date_debut).total_seconds() // 60)
        heures, reste = divmod(minutes, 60)
        if not heures:
            return f"{reste} min"
        return f"{heures} h {reste:02d}" if reste else f"{heures} h"

    # ------------------------------------------------------------------ places
    def nb_inscrits(self):
        if hasattr(self, 'n_inscrits'):
            return self.n_inscrits
        return self.participations.count()

    def places_restantes(self):
        if not self.places:
            return None
        return max(self.places - self.nb_inscrits(), 0)

    def est_complet(self):
        return bool(self.places) and self.places_restantes() == 0

    @property
    def attestation_payante(self):
        return self.prix_attestation > 0

    # ------------------------------------------------------------------ présentation
    @property
    def theme_libelle(self):
        return THEMES.get(self.theme, THEMES['autre'])[0]

    @property
    def theme_icone(self):
        return THEMES.get(self.theme, THEMES['autre'])[1]

    @property
    def theme_style(self):
        _, _, a, b = THEMES.get(self.theme, THEMES['autre'])
        return f"--wb-a:{a};--wb-b:{b}"

    def points_cles_list(self):
        return [l.strip().lstrip('-•*–').strip() for l in (self.points_cles or '').splitlines()
                if l.strip().lstrip('-•*–').strip()]

    def paragraphes(self):
        return [p.strip() for p in (self.description or '').replace('\r\n', '\n').split('\n\n') if p.strip()]

    @property
    def youtube_id(self):
        """Identifiant (11 caractères) de la vidéo YouTube, quel que soit le format du lien collé."""
        valeur = (self.youtube_direct or '').strip()
        if YOUTUBE_ID.fullmatch(valeur):
            return valeur
        trouve = YOUTUBE_LIEN.search(valeur)
        return trouve.group(1) if trouve else ''

    def get_salle_url(self):
        base_url = (getattr(settings, 'JITSI_BASE_URL', '') or '').rstrip('/')
        return f"{base_url}/{self.salle_jitsi}" if base_url and self.salle_jitsi else ''


def _code_verification():
    return secrets.token_hex(8)


class ParticipationWebinaire(RelancePaiementMixin):
    webinaire = models.ForeignKey(Webinaire, on_delete=models.CASCADE, related_name='participations')
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='participations_webinaires',
                                    verbose_name="Compte")
    prenom = models.CharField("Prénom", max_length=100)
    nom = models.CharField(max_length=100)
    email = models.EmailField()
    inscrit_le = models.DateTimeField("Inscrit le", auto_now_add=True)
    rejoint_le = models.DateTimeField("A rejoint la séance le", null=True, blank=True,
                                      help_text="Renseigné à l'entrée dans la salle : ouvre le droit à l'attestation.")
    code_verification = models.CharField("Code de vérification", max_length=32, unique=True,
                                         default=_code_verification, editable=False)
    # Attestation payante : montant figé au lancement du paiement
    montant_attestation = models.PositiveIntegerField("Attestation : montant (FCFA)", null=True, blank=True)
    fedapay_attestation_id = models.CharField(max_length=100, blank=True)
    attestation_payee_le = models.DateTimeField("Attestation payée le", null=True, blank=True)

    class Meta:
        ordering = ['-inscrit_le']
        verbose_name = "Participant"
        verbose_name_plural = "Participants"
        constraints = [
            models.UniqueConstraint(fields=['webinaire', 'utilisateur'], name='participation_webinaire_unique'),
        ]

    def __str__(self):
        return f"{self.nom_complet} — {self.webinaire.titre}"

    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}".strip()

    @property
    def numero_attestation(self):
        return f"KCO-WEB-{self.webinaire.date_debut:%Y}-{self.pk:05d}"

    @property
    def a_participe(self):
        return self.rejoint_le is not None

    @property
    def montant_attestation_du(self):
        return self.montant_attestation if self.montant_attestation is not None else self.webinaire.prix_attestation

    @property
    def attestation_reglee(self):
        """Attestation gratuite, ou payée."""
        return not self.webinaire.attestation_payante or self.attestation_payee_le is not None

    def attestation_disponible(self, maintenant=None):
        return self.a_participe and self.attestation_reglee and self.webinaire.statut(maintenant) == 'termine'
