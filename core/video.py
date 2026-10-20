"""
Liens vidéo YouTube / TikTok : reconnaissance, miniature, lecteur intégré.

Aucune vidéo ni image n'est stockée sur le serveur : seul le lien est enregistré,
l'aperçu (miniature) et la lecture sont servis par YouTube ou TikTok.
"""
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

from django.core.exceptions import ValidationError

YOUTUBE_HOSTS = {'youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com',
                 'youtu.be', 'www.youtube-nocookie.com', 'youtube-nocookie.com'}
TIKTOK_HOSTS = {'tiktok.com', 'www.tiktok.com', 'm.tiktok.com', 'vm.tiktok.com', 'vt.tiktok.com'}
YOUTUBE_ID = re.compile(r'^[A-Za-z0-9_-]{11}$')
TIKTOK_ID = re.compile(r'/video/(\d{8,25})')


@dataclass(frozen=True)
class Video:
    plateforme: str          # 'youtube' | 'tiktok'
    identifiant: str
    url: str                 # lien d'origine (ouvrir sur la plateforme)

    @property
    def est_youtube(self):
        return self.plateforme == 'youtube'

    @property
    def est_tiktok(self):
        return self.plateforme == 'tiktok'

    @property
    def vertical(self):
        """TikTok et YouTube Shorts : format portrait."""
        return self.est_tiktok or '/shorts/' in self.url

    @property
    def miniature(self):
        """Miniature hébergée par YouTube (TikTok ne fournit pas de miniature stable)."""
        if self.est_youtube:
            return f"https://i.ytimg.com/vi/{self.identifiant}/hqdefault.jpg"
        return ''

    @property
    def miniature_hd(self):
        """1280 × 720 : n'existe que pour les vidéos mises en ligne en HD (sinon repli, voir video.js)."""
        if self.est_youtube:
            return f"https://i.ytimg.com/vi/{self.identifiant}/maxresdefault.jpg"
        return ''

    @property
    def miniature_sd(self):
        """640 × 480, disponible pour presque toutes les vidéos."""
        if self.est_youtube:
            return f"https://i.ytimg.com/vi/{self.identifiant}/sddefault.jpg"
        return ''

    @property
    def miniatures_repli(self):
        """Miniatures de repli (de la meilleure à la plus sûre), séparées par des espaces."""
        return f"{self.miniature_sd} {self.miniature}" if self.est_youtube else ''

    @property
    def lecteur(self):
        """URL du lecteur intégré (chargé au clic, lecture automatique)."""
        if self.est_youtube:
            return f"https://www.youtube-nocookie.com/embed/{self.identifiant}?autoplay=1&rel=0&modestbranding=1"
        return f"https://www.tiktok.com/player/v1/{self.identifiant}?autoplay=1&rel=0&description=1"

    @property
    def lien_plateforme(self):
        if self.est_youtube:
            return f"https://www.youtube.com/watch?v={self.identifiant}"
        return self.url

    @property
    def nom_plateforme(self):
        return 'YouTube' if self.est_youtube else 'TikTok'


def _youtube_id(parsed):
    host = parsed.netloc.lower()
    chemin = [p for p in parsed.path.split('/') if p]
    if host == 'youtu.be':
        candidat = chemin[0] if chemin else ''
    elif chemin and chemin[0] in ('shorts', 'embed', 'live', 'v') and len(chemin) > 1:
        candidat = chemin[1]
    else:
        candidat = (parse_qs(parsed.query).get('v') or [''])[0]
    return candidat if YOUTUBE_ID.match(candidat or '') else ''


def analyser(url):
    """Retourne un objet Video, ou None si le lien n'est pas une vidéo YouTube / TikTok reconnue."""
    url = (url or '').strip()
    if not url:
        return None
    if not url.startswith(('http://', 'https://')):
        url = f"https://{url}"
    parsed = urlparse(url)
    host = parsed.netloc.lower().split(':')[0]
    if host in YOUTUBE_HOSTS:
        identifiant = _youtube_id(parsed)
        return Video('youtube', identifiant, url) if identifiant else None
    if host in TIKTOK_HOSTS:
        trouve = TIKTOK_ID.search(parsed.path)
        return Video('tiktok', trouve.group(1), url.split('?')[0]) if trouve else None
    return None


def resoudre_lien_court(url, timeout=6):
    """Lien court TikTok (vm.tiktok.com/…) -> lien complet. Retourne l'URL d'origine si impossible."""
    try:
        import requests
        reponse = requests.head(url, allow_redirects=True, timeout=timeout,
                                headers={'User-Agent': 'Mozilla/5.0 (KcoMat)'})
        return reponse.url or url
    except Exception:
        return url


def valider_lien_video(url):
    """Validateur de champ : YouTube ou TikTok uniquement."""
    if not url:
        return
    if analyser(url) is None:
        raise ValidationError(
            "Lien non reconnu. Collez le lien d'une vidéo YouTube (youtube.com/watch?v=…, youtu.be/…, "
            "youtube.com/shorts/…) ou TikTok (tiktok.com/@compte/video/…)."
        )


def normaliser_lien_video(url):
    """À appeler avant validation : déplie les liens courts TikTok (vm.tiktok.com/…)."""
    url = (url or '').strip()
    if url and analyser(url) is None and urlparse(url if '://' in url else f'https://{url}').netloc.lower() in (
            'vm.tiktok.com', 'vt.tiktok.com'):
        url = resoudre_lien_court(url if '://' in url else f'https://{url}')
    return url
