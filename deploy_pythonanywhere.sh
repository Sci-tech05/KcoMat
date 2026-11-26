#!/usr/bin/env bash
# =============================================================================
# Déploiement KcoMat sur PythonAnywhere (à lancer dans une console Bash) :
#     bash deploy_pythonanywhere.sh
#
# - Sauvegarde .env, la base et les médias (jamais versionnés) avant la mise à jour
# - Aligne le code sur GitHub (branche main), puis remet les médias en place
# - Dépendances, migrations, fichiers statiques, nettoyage des caches Python
# - Recharge le site (équivalent du bouton « Reload » de l'onglet Web)
# =============================================================================
set -euo pipefail

PROJET="${PROJET:-$HOME/KcoMat}"
VENV="${VENV:-$HOME/.virtualenvs/venv}"
WSGI="${WSGI:-/var/www/$(echo "${USER}" | tr 'A-Z' 'a-z')_pythonanywhere_com_wsgi.py}"
SAUVEGARDES="$HOME/sauvegardes_kcomat"
SAUVEGARDE="$SAUVEGARDES/$(date +%Y%m%d-%H%M%S)"
# Sauvegardes complètes conservées (chacune contient la base et tous les médias : le quota disque
# de PythonAnywhere est vite atteint)
GARDER="${GARDER:-2}"

cd "$PROJET"

# Téléchargement d'abord : un échec d'identification GitHub ne laisse aucune sauvegarde derrière lui
echo "→ Téléchargement du code depuis GitHub"
git fetch origin

# Sauvegardes interrompues (sans fichier .complete) : inutilisables, on libère la place
for dossier in "$SAUVEGARDES"/*/; do
    if [ -d "$dossier" ] && [ ! -f "$dossier/.complete" ]; then
        rm -rf "$dossier"
        echo "  Sauvegarde incomplète supprimée : $dossier"
    fi
done
# Place pour la nouvelle : on ne garde que les GARDER-1 plus récentes
ls -1d "$SAUVEGARDES"/*/ 2>/dev/null | sort -r | tail -n +"$GARDER" | xargs -r rm -rf   # noms = dates

echo "→ Sauvegarde dans $SAUVEGARDE"
echec_sauvegarde() {
    rm -rf "$SAUVEGARDE"
    echo "✗ Sauvegarde impossible (quota disque ?) : rien n'a été modifié sur le site."
    echo "  Place occupée :  du -sh ~/sauvegardes_kcomat/* ~/KcoMat/media ~/KcoMat/db.sqlite3 ~/.cache"
    exit 1
}
trap echec_sauvegarde ERR
mkdir -p "$SAUVEGARDE"
if [ -f .env ]; then cp -a .env "$SAUVEGARDE/"; else echo "  (pas de .env à sauvegarder)"; fi
if [ -f db.sqlite3 ]; then cp -a db.sqlite3 "$SAUVEGARDE/"; else echo "  (pas de base SQLite à sauvegarder)"; fi
# media/cache (copies WebP redimensionnées, aperçus de partage) se régénère : inutile de le sauvegarder
if [ -d media ]; then
    if command -v rsync >/dev/null; then
        rsync -a --exclude 'cache/' media/ "$SAUVEGARDE/media/"
    else
        cp -a media "$SAUVEGARDE/media" && rm -rf "$SAUVEGARDE/media/cache"
    fi
fi
# CV et lettres de motivation (hors de media/, jamais servis publiquement)
if [ -d documents_prives ]; then
    cp -a documents_prives "$SAUVEGARDE/documents_prives"
fi
touch "$SAUVEGARDE/.complete"
trap - ERR

echo "→ Mise à jour du code"
git reset --hard origin/main

echo "→ Restauration des fichiers non versionnés"
[ -f .env ] || cp -a "$SAUVEGARDE/.env" . 2>/dev/null || true
[ -f db.sqlite3 ] || cp -a "$SAUVEGARDE/db.sqlite3" . 2>/dev/null || true
if [ -d "$SAUVEGARDE/media" ]; then
    mkdir -p media
    cp -an "$SAUVEGARDE/media/." media/      # ne remplace rien d'existant
fi
if [ -d "$SAUVEGARDE/documents_prives" ]; then
    mkdir -p documents_prives
    cp -an "$SAUVEGARDE/documents_prives/." documents_prives/
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate"
echo "→ Dépendances Python"
pip install --quiet -r requirements.txt
echo "→ Migrations de la base"
python manage.py migrate --noinput
echo "→ Table du cache partagé (anti-essais de connexion, codes 2FA)"
python manage.py createcachetable
echo "→ Fichiers statiques : copie + compression gzip"
echo "  (1 à 3 minutes la première fois ; ensuite seuls les fichiers modifiés sont retraités)"
debut=$(date +%s)
python manage.py collectstatic --noinput --verbosity 1
echo "  Terminé en $(( $(date +%s) - debut )) s."

echo "→ Nettoyage des caches Python (recréés automatiquement par Python au besoin)"
find . -path ./node_modules -prune -o -type d -name __pycache__ -prune -exec rm -rf {} +

echo "→ Rechargement du site"
if [ -f "$WSGI" ]; then
    touch "$WSGI"
    echo "  Site rechargé ($WSGI)."
else
    echo "  Fichier WSGI introuvable : cliquez sur « Reload » dans l'onglet Web."
fi

echo "✓ Déploiement terminé. Sauvegarde : $SAUVEGARDE"
