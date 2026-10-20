import os
import re
import uuid

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


def _lignes(texte):
    """Texte « une entrée par ligne » -> liste (puces « - », « • », « * » retirées)."""
    lignes = []
    for ligne in (texte or '').splitlines():
        ligne = ligne.strip().lstrip('-•*–').strip()
        if ligne:
            lignes.append(ligne)
    return lignes


class Offre(models.Model):
    TYPE_CHOICES = [
        ('emploi', 'Emploi'),
        ('stage', 'Stage'),
        ('freelance', 'Freelance'),
    ]
    DOMAINE_CHOICES = [
        ('domotique', 'Domotique & IoT'),
        ('electricite_batiment', 'Électricité bâtiment'),
        ('electricite_industrielle', 'Électricité industrielle & automatisme'),
        ('electronique', 'Électronique & systèmes embarqués'),
        ('web_mobile', 'Développement web & mobile'),
        ('ia', 'Intelligence artificielle & data'),
        ('drones', 'Drones & télépilotage'),
        ('solaire', 'Énergie solaire photovoltaïque'),
        ('securite', 'Sécurité informatique & réseaux'),
        ('videosurveillance', 'Vidéosurveillance & sécurité électronique'),
        ('commercial', 'Vente & relation client'),
        ('autre', 'Autre'),
    ]
    DOMAINE_ICONS = {
        'domotique': 'home', 'electricite_batiment': 'zap', 'electricite_industrielle': 'bot',
        'electronique': 'cpu', 'web_mobile': 'grid', 'ia': 'sparkles', 'drones': 'rocket',
        'solaire': 'sun', 'securite': 'shield', 'videosurveillance': 'camera', 'commercial': 'bag',
    }
    NATURE_CHOICES = [
        ('frais', 'Frais de stage (payés par le stagiaire)'),
        ('remuneration', 'Rémunération (versée par KcoMat)'),
    ]

    titre = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    type_offre = models.CharField("Catégorie", max_length=20, choices=TYPE_CHOICES, default='emploi')
    domaine = models.CharField(max_length=150, choices=DOMAINE_CHOICES, default='autre')
    image = models.ImageField(
        upload_to='offres/', blank=True, null=True,
        help_text="Obligatoire pour publier l'offre. Format paysage conseillé (1600 × 1000 px).",
    )
    accroche = models.CharField(
        max_length=220, blank=True,
        help_text="Résumé d'une ou deux phrases, affiché sur la carte de l'offre.",
    )
    description = models.TextField("Le poste")
    missions = models.TextField("Missions", blank=True, help_text="Une mission par ligne.")
    competences_requises = models.TextField(
        "Compétences requises",
        help_text="Une compétence par ligne, au format « Domaine : détail » (ex. « Électricité : lecture de schémas »).",
    )
    profil = models.TextField("Profil recherché", blank=True, help_text="Une qualité par ligne.")
    avantages = models.TextField("Ce que vous gagnez", blank=True, help_text="Un avantage par ligne.")
    niveau_requis = models.CharField(max_length=150, blank=True, help_text="Ex. « BTS / Licence en électrotechnique ».")
    localite = models.CharField(max_length=100, default='Lokossa, Bénin')
    nature_montant = models.CharField(
        "Nature du montant", max_length=20, choices=NATURE_CHOICES, default='frais',
        help_text="Indique si les montants des formules sont des frais payés par le candidat ou une rémunération.",
    )
    remuneration = models.CharField(
        "Montant (texte libre)", max_length=100, blank=True,
        help_text="Affiché seulement s'il n'y a aucune formule (ex. « Selon profil », « Sur devis »).",
    )
    places = models.PositiveSmallIntegerField("Places disponibles", null=True, blank=True)
    date_limite = models.DateField(null=True, blank=True)
    mise_en_avant = models.BooleanField("À la une", default=False)
    actif = models.BooleanField("Publiée", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-mise_en_avant', '-created_at']
        verbose_name = "Offre"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.titre)
        super().save(*args, **kwargs)

    def clean(self):
        if self.actif and not self.image:
            raise ValidationError({'actif': "Ajoutez une image avant de publier l'offre."})

    def __str__(self):
        return f"[{self.get_type_offre_display()}] {self.titre}"

    # -- Affichage -----------------------------------------------------------
    @property
    def domaine_icon(self):
        return self.DOMAINE_ICONS.get(self.domaine, 'briefcase')

    @property
    def est_cloturee(self):
        return bool(self.date_limite and self.date_limite < timezone.localdate())

    @property
    def jours_restants(self):
        if not self.date_limite:
            return None
        return (self.date_limite - timezone.localdate()).days

    @property
    def resume(self):
        """Accroche, ou à défaut le début de la description (offres saisies sans accroche)."""
        from django.utils.text import Truncator
        return self.accroche or Truncator(' '.join((self.description or '').split())).chars(150)

    @property
    def libelle_montant(self):
        return 'Frais de stage' if self.nature_montant == 'frais' else 'Rémunération'

    def missions_list(self):
        return _lignes(self.missions)

    def profil_list(self):
        from .catalogue import PROFIL_TYPE
        return _lignes(self.profil) or [PROFIL_TYPE.get(self.type_offre, '')]

    def avantages_list(self):
        """Avantages saisis, sinon ceux par défaut de la catégorie (stage / emploi / freelance)."""
        from .catalogue import AVANTAGES
        return _lignes(self.avantages) or list(AVANTAGES.get(self.type_offre, []))

    def competences_list(self):
        """[(libellé, détail)] : « Électricité : lecture de schémas » -> ('Électricité', 'lecture de schémas')."""
        items = []
        for ligne in _lignes(self.competences_requises):
            libelle, sep, detail = ligne.partition(':')
            items.append((libelle.strip(), detail.strip()) if sep and len(libelle) <= 40 else ('', ligne))
        return items

    def prix_min(self):
        montants = [f.montant for f in self.formules.all() if f.montant is not None]
        return min(montants) if montants else None


class FormuleOffre(models.Model):
    """Durée et montant proposés pour une offre (ex. 1 mois · 20 000 FCFA)."""
    offre = models.ForeignKey(Offre, on_delete=models.CASCADE, related_name='formules')
    duree = models.CharField("Durée", max_length=60, help_text="Ex. « 1 mois », « 3 mois et plus ».")
    montant = models.PositiveIntegerField("Montant (FCFA)", null=True, blank=True,
                                          help_text="Laisser vide pour « Sur devis ».")
    description = models.CharField(max_length=160, blank=True, help_text="Ex. « Découverte du métier ».")
    recommandee = models.BooleanField("Recommandée", default=False)
    ordre = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['ordre', 'montant']
        verbose_name = "Formule (durée & montant)"
        verbose_name_plural = "Formules (durée & montant)"

    def __str__(self):
        montant = f"{self.montant:,} FCFA".replace(',', ' ') if self.montant is not None else 'Sur devis'
        return f"{self.duree} · {montant}"


# ---------------------------------------------------------------------------
# Fichiers de candidature : formats et taille contrôlés, noms imprévisibles
# (les CV contiennent des données personnelles).
# ---------------------------------------------------------------------------
DOCUMENT_EXTENSIONS = ['pdf', 'doc', 'docx']
DOCUMENT_MAX_MB = 5


def validate_document_size(file):
    if file and file.size > DOCUMENT_MAX_MB * 1024 * 1024:
        raise ValidationError(f"Le fichier dépasse {DOCUMENT_MAX_MB} Mo.")


def _document_path(folder, instance, filename):
    extension = os.path.splitext(filename)[1].lower()
    return f"candidatures/{folder}/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{extension}"


def cv_upload_to(instance, filename):
    return _document_path('cv', instance, filename)


def lettre_upload_to(instance, filename):
    return _document_path('lettres', instance, filename)


DOCUMENT_VALIDATORS = [FileExtensionValidator(DOCUMENT_EXTENSIONS), validate_document_size]


class Candidature(models.Model):
    STATUT_NOUVELLE = 'nouvelle'
    STATUT_EN_REVUE = 'en_revue'
    STATUT_PRESELECTIONNEE = 'preselectionnee'
    STATUT_ENTRETIEN = 'entretien'
    STATUT_RETENUE = 'retenue'
    STATUT_REFUSEE = 'refusee'
    STATUT_CHOICES = [
        (STATUT_NOUVELLE, 'Nouvelle'),
        (STATUT_EN_REVUE, 'En revue'),
        (STATUT_PRESELECTIONNEE, 'Présélectionnée'),
        (STATUT_ENTRETIEN, 'Entretien'),
        (STATUT_RETENUE, 'Retenue'),
        (STATUT_REFUSEE, 'Refusée'),
    ]
    STATUTS_CLOS = (STATUT_RETENUE, STATUT_REFUSEE)
    NOTE_CHOICES = [(n, '★' * n + '☆' * (5 - n)) for n in range(1, 6)]

    offre = models.ForeignKey(Offre, on_delete=models.CASCADE, related_name='candidatures')
    formule = models.ForeignKey(FormuleOffre, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='candidatures', verbose_name="Formule choisie")
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    email = models.EmailField()
    telephone = models.CharField(max_length=20)
    cv = models.FileField(upload_to=cv_upload_to, validators=DOCUMENT_VALIDATORS)
    lettre_motivation = models.FileField(upload_to=lettre_upload_to, blank=True, null=True, validators=DOCUMENT_VALIDATORS)
    message = models.TextField("Motivation", blank=True, max_length=1500)

    # Suivi par l'équipe
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default=STATUT_NOUVELLE, db_index=True)
    note = models.PositiveSmallIntegerField(
        "Potentiel", choices=NOTE_CHOICES, null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Évaluation de l'équipe, de 1 à 5 étoiles.",
    )
    score_auto = models.PositiveSmallIntegerField(
        "Pré-score", default=0, editable=False,
        help_text="Calculé automatiquement (0-100) à partir de la complétude du dossier.",
    )
    notes_internes = models.TextField("Notes internes", blank=True)
    statut_modifie_le = models.DateTimeField(null=True, blank=True, editable=False)
    reponse_envoyee_le = models.DateTimeField("Réponse envoyée le", null=True, blank=True, editable=False)
    traite = models.BooleanField(default=False, editable=False)  # = statut clos (compatibilité)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Candidature"

    def __str__(self):
        return f"{self.prenom} {self.nom} → {self.offre.titre}"

    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}".strip()

    # -- Pré-score automatique ------------------------------------------------
    def score_details(self):
        """Critères simples et transparents : [(libellé, points obtenus, points max)]."""
        details = []
        cv_name = (self.cv.name if self.cv else '').lower()
        details.append(("CV au format PDF", 20 if cv_name.endswith('.pdf') else (10 if cv_name else 0), 20))
        details.append(("Lettre de motivation jointe", 25 if self.lettre_motivation else 0, 25))
        longueur = len((self.message or '').strip())
        details.append(("Motivation rédigée", 25 if longueur >= 300 else 15 if longueur >= 120 else 5 if longueur else 0, 25))
        chiffres = re.sub(r'\D', '', self.telephone or '')
        details.append(("Téléphone complet", 10 if len(chiffres) >= 10 else 0, 10))
        reference = timezone.localdate(self.created_at) if self.created_at else timezone.localdate()
        dans_les_delais = not self.offre_id or not self.offre.date_limite or reference <= self.offre.date_limite
        details.append(("Envoyée avant la date limite", 20 if dans_les_delais else 0, 20))
        return details

    def calculer_score(self):
        return min(100, sum(points for _, points, _ in self.score_details()))

    def save(self, *args, **kwargs):
        if self.pk:
            ancien_statut = Candidature.objects.filter(pk=self.pk).values_list('statut', flat=True).first()
            if ancien_statut and ancien_statut != self.statut:
                self.statut_modifie_le = timezone.now()
        self.traite = self.statut in self.STATUTS_CLOS
        self.score_auto = self.calculer_score()
        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            kwargs['update_fields'] = set(update_fields) | {'traite', 'score_auto', 'statut_modifie_le'}
        super().save(*args, **kwargs)
