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
SAUVEGARDE="$HOME/sauvegardes_kcomat/$(date +%Y%m%d-%H%M%S)"

cd "$PROJET"
echo "→ Sauvegarde dans $SAUVEGARDE"
mkdir -p "$SAUVEGARDE"
cp -a .env "$SAUVEGARDE/" 2>/dev/null || echo "  (pas de .env à sauvegarder)"
cp -a db.sqlite3 "$SAUVEGARDE/" 2>/dev/null || echo "  (pas de base SQLite à sauvegarder)"
[ -d media ] && cp -a media "$SAUVEGARDE/media"

echo "→ Mise à jour du code depuis GitHub"
git fetch origin
git reset --hard origin/main

echo "→ Restauration des fichiers non versionnés"
[ -f .env ] || cp -a "$SAUVEGARDE/.env" . 2>/dev/null || true
[ -f db.sqlite3 ] || cp -a "$SAUVEGARDE/db.sqlite3" . 2>/dev/null || true
if [ -d "$SAUVEGARDE/media" ]; then
    mkdir -p media
    cp -an "$SAUVEGARDE/media/." media/      # ne remplace rien d'existant
fi

echo "→ Dépendances, migrations, fichiers statiques"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip install --quiet -r requirements.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput --verbosity 0

echo "→ Nettoyage des caches Python (recréés automatiquement par Python au besoin)"
find . -path ./node_modules -prune -o -type d -name __pycache__ -prune -exec rm -rf {} +

echo "→ Rechargement du site"
if [ -f "$WSGI" ]; then
    touch "$WSGI"
    echo "  Site rechargé ($WSGI)."
else
    echo "  Fichier WSGI introuvable : cliquez sur « Reload » dans l'onglet Web."
fi

# Garde les 5 dernières sauvegardes
ls -1dt "$HOME"/sauvegardes_kcomat/*/ 2>/dev/null | tail -n +6 | xargs -r rm -rf
echo "✓ Déploiement terminé. Sauvegarde : $SAUVEGARDE"
