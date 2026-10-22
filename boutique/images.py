"""
Import d'une image produit depuis un lien : téléchargée une seule fois, puis
redressée, réduite (1200 px max) et enregistrée en WebP (~50-150 Ko) dans les médias du site.
L'image n'est jamais affichée depuis le site d'origine (pas de dépendance, pas de photo de plusieurs Mo).
"""
import ipaddress
import socket
from io import BytesIO
from urllib.parse import urljoin, urlparse

import requests
from django.core.exceptions import ValidationError

from core.images import REGLAGES, compresser as compresser_image

TAILLE_MAX_OCTETS = 15 * 1024 * 1024
REDIRECTIONS_MAX = 3


def _verifier_adresse(url):
    """Refuse tout ce qui n'est pas un lien web public (protège le serveur et son réseau interne)."""
    lien = urlparse(url)
    if lien.scheme not in ('http', 'https') or not lien.hostname:
        raise ValidationError("Le lien doit commencer par http:// ou https://.")
    try:
        adresses = {info[4][0] for info in socket.getaddrinfo(lien.hostname, lien.port or 443)}
    except socket.gaierror:
        raise ValidationError("Site introuvable : vérifiez le lien.")
    for adresse in adresses:
        ip = ipaddress.ip_address(adresse.split('%')[0])
        if not ip.is_global:
            raise ValidationError("Ce lien pointe vers une adresse interne : utilisez le lien public de l'image.")


def _telecharger(url):
    for _ in range(REDIRECTIONS_MAX + 1):
        _verifier_adresse(url)
        try:
            reponse = requests.get(url, stream=True, timeout=15, allow_redirects=False,
                                   headers={'User-Agent': 'KcoMat/1.0 (import image produit)'})
        except requests.RequestException:
            raise ValidationError("Impossible de télécharger l'image : le site ne répond pas.")
        if reponse.is_redirect:
            url = urljoin(url, reponse.headers.get('Location', ''))
            reponse.close()
            continue
        if reponse.status_code != 200:
            raise ValidationError(f"Le site a refusé l'accès à l'image (code {reponse.status_code}).")
        if not reponse.headers.get('Content-Type', '').startswith('image/'):
            raise ValidationError("Ce lien n'est pas une image : faites clic droit sur l'image → « Copier l'adresse de l'image ».")
        contenu = BytesIO()
        for bloc in reponse.iter_content(64 * 1024):
            contenu.write(bloc)
            if contenu.tell() > TAILLE_MAX_OCTETS:
                raise ValidationError("Image trop lourde (plus de 15 Mo).")
        return contenu
    raise ValidationError("Trop de redirections : utilisez le lien direct de l'image.")


def compresser(fichier):
    """Compression d'une photo produit : 1200 px max, fond blanc, WebP (voir core/images.py)."""
    return compresser_image(fichier, **REGLAGES['boutique.produit'])


def image_depuis_lien(url):
    """Télécharge l'image du lien et renvoie un fichier WebP compressé, prêt pour un ImageField."""
    return compresser(_telecharger(url.strip()))
