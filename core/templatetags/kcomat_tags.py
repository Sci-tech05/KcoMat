import logging
import os
from pathlib import Path

from django import template
from django.conf import settings
from django.utils.encoding import filepath_to_uri
from django.utils.safestring import mark_safe
from PIL import Image, ImageOps

register = template.Library()
logger = logging.getLogger(__name__)

WEBP_CACHE_DIR = 'cache/webp'
WEBP_SKIP_SUFFIXES = {'.gif', '.svg', '.webp'}


@register.filter
def webp(image, width=800):
    """
    URL d'une copie WebP redimensionnée d'une image uploadée (générée une fois,
    regénérée si l'original change). Renvoie l'URL d'origine en cas de souci.
    Usage : <img src="{{ formation.image|webp:800 }}">
    """
    if not image:
        return ''
    try:
        original_url = image.url
        source = Path(image.path)
    except (ValueError, NotImplementedError):
        return ''
    if source.suffix.lower() in WEBP_SKIP_SUFFIXES:
        return original_url

    try:
        width = max(16, int(width))
        relative = Path(WEBP_CACHE_DIR, str(width), image.name).with_suffix('.webp')
        target = Path(settings.MEDIA_ROOT, relative)
        if not target.exists() or target.stat().st_mtime < source.stat().st_mtime:
            target.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(source) as img:
                img = ImageOps.exif_transpose(img)
                has_alpha = img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)
                img = img.convert('RGBA' if has_alpha else 'RGB')
                if img.width > width:
                    img.thumbnail((width, width * 10), Image.LANCZOS)
                temp = target.with_name(target.name + '.tmp')
                img.save(temp, 'WEBP', quality=80, method=4)
            os.replace(temp, target)
        return settings.MEDIA_URL + filepath_to_uri(relative.as_posix())
    except Exception:
        logger.warning("Conversion WebP impossible pour %s", image.name, exc_info=True)
        return original_url


OG_CACHE_DIR = 'cache/og'
OG_TAILLE = (1200, 630)


@register.filter
def og_image(image):
    """
    URL d'une image d'aperçu de partage (WhatsApp, Facebook, LinkedIn) : JPEG 1200 × 630
    recadré au centre, léger (< 300 Ko), générée une fois. Renvoie '' en cas de souci.
    Usage : <meta property="og:image" content="{{ SITE_URL }}{{ formation.image|og_image }}">
    """
    if not image:
        return ''
    try:
        source = Path(image.path)
        relative = Path(OG_CACHE_DIR, image.name).with_suffix('.jpg')
        target = Path(settings.MEDIA_ROOT, relative)
        if not target.exists() or target.stat().st_mtime < source.stat().st_mtime:
            target.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(source) as img:
                img = ImageOps.exif_transpose(img)
                if img.mode in ('RGBA', 'LA', 'P'):
                    # transparence -> fond blanc (le JPEG n'a pas de canal alpha)
                    img = img.convert('RGBA')
                    fond = Image.new('RGB', img.size, (255, 255, 255))
                    fond.paste(img, mask=img.split()[-1])
                    img = fond
                img = ImageOps.fit(img.convert('RGB'), OG_TAILLE, Image.LANCZOS)
                temp = target.with_name(target.name + '.tmp')
                img.save(temp, 'JPEG', quality=82, optimize=True, progressive=True)
            os.replace(temp, target)
        return settings.MEDIA_URL + filepath_to_uri(relative.as_posix())
    except Exception:
        logger.warning("Image de partage impossible pour %s", getattr(image, 'name', image), exc_info=True)
        try:
            return image.url
        except ValueError:
            return ''


@register.filter
def split(value, delimiter=','):
    """Split a string by delimiter and return a list. Usage: {{ value|split:"," }}"""
    if value:
        return [item.strip() for item in str(value).split(delimiter) if item.strip()]
    return []


@register.filter
def index(lst, i):
    """Get item at index from list. Usage: {{ mylist|index:0 }}"""
    try:
        return lst[int(i)]
    except (IndexError, TypeError, ValueError):
        return ''


@register.filter
def multiply(value, factor):
    """Multiply value by factor. Usage: {{ price|multiply:1.1 }}"""
    try:
        return int(value) * int(factor)
    except (TypeError, ValueError):
        return 0


class CaptureNode(template.Node):
    child_nodelists = ('nodelist',)

    def __init__(self, nodelist, var_name):
        self.nodelist = nodelist
        self.var_name = var_name

    def render(self, context):
        # Espaces/retours à la ligne fusionnés : utilisable dans un attribut HTML.
        context[self.var_name] = mark_safe(' '.join(self.nodelist.render(context).split()))
        return ''


@register.filter
def remplissage_etoiles(note):
    """Note (ex. 4.3) -> remplissage des 5 étoiles en % : [100, 100, 100, 100, 50] (arrondi à la demi-étoile)."""
    try:
        demis = round(float(note or 0) * 2)
    except (TypeError, ValueError):
        demis = 0
    return [100 if demis >= 2 * n else 50 if demis == 2 * n - 1 else 0 for n in range(1, 6)]


@register.tag
def capture(parser, token):
    """
    Rend un contenu (blocs compris) dans une variable, sans l'afficher.
    Usage : {% capture as page_title %}{% block title %}{% endblock %}{% endcapture %}
    """
    bits = token.split_contents()
    if len(bits) != 3 or bits[1] != 'as':
        raise template.TemplateSyntaxError("Usage : {% capture as nom_variable %}...{% endcapture %}")
    nodelist = parser.parse(('endcapture',))
    parser.delete_first_token()
    return CaptureNode(nodelist, bits[2])


SERVICE_ICONS = [
    (('formation', 'cours'), 'graduation'),  # avant « site » (ex. « Formation sur site »)
    (('web', 'mobile', 'logiciel', 'application', 'site'), 'grid'),
    (('domotique', 'iot', 'maison'), 'home'),
    (('solaire', 'photovolta'), 'sun'),
    (('caméra', 'camera', 'surveillance'), 'camera'),
    (('sécurité', 'securite', 'cyber'), 'shield'),
    (('automatisation', 'robot', 'intelligence', ' ia'), 'bot'),
    (('dépannage', 'depannage', 'maintenance', 'réparation'), 'wrench'),
    (('drone',), 'rocket'),
    (('électri', 'electri', 'installation'), 'zap'),
    (('électronique', 'electronique', 'composant'), 'cpu'),
]


@register.filter
def service_icon(title):
    """Nom d'icône (partials/icon.html) déduit du titre d'un service."""
    text = f" {str(title or '').lower()}"
    for keywords, icon in SERVICE_ICONS:
        if any(keyword in text for keyword in keywords):
            return icon
    return 'sparkles'


COMPETENCE_ICONS = [
    (('savoir', 'soft', 'qualit'), 'users'),
    (('sécurité', 'securite', 'cyber'), 'shield'),
    (('norme', 'réglementation', 'reglementation'), 'badge-check'),
    (('communication',), 'message'),
    (('réseau', 'reseau', 'protocole'), 'wifi'),
    (('programmation', 'web', 'informatique', 'système', 'systeme', 'outils', 'bases de données'), 'grid'),
    (('électronique', 'electronique', 'automatisme', 'équipement'), 'cpu'),
    (('électri', 'electri', 'électrotechnique'), 'zap'),
    (('solaire', 'dimensionnement'), 'sun'),
    (('pilotage', 'drone'), 'rocket'),
    (('ia', 'données', 'donnees', 'image'), 'sparkles'),
    (('outillage', 'technique', 'lecture'), 'wrench'),
    (('commerce', 'vente', 'numérique'), 'bag'),
]


@register.filter
def competence_icon(label):
    """Icône déduite du libellé d'une compétence (« Électricité », « Réseaux »…)."""
    text = str(label or '').lower()
    for keywords, icon in COMPETENCE_ICONS:
        if any(text.startswith(k) or f' {k}' in f' {text}' for k in keywords):
            return icon
    return 'check'


@register.filter
def domaine_icon(cle):
    """Icône d'un domaine d'offre (carrieres.Offre.DOMAINE_ICONS)."""
    from carrieres.models import Offre
    return Offre.DOMAINE_ICONS.get(cle, 'briefcase')


@register.simple_tag
def partenaires_actifs(limite=12):
    """Partenaires à afficher (footer, page Contact), gérés dans l'admin : Partenariats › Partenaires."""
    from partenariats.models import Partenaire
    return list(Partenaire.objects.filter(actif=True).order_by('ordre', 'nom')[:limite])


@register.filter
def video(url):
    """Lien YouTube / TikTok -> objet Video (miniature, lecteur…), ou None. Usage : {% with v=projet.lien_video|video %}"""
    from core.video import analyser
    return analyser(url)
