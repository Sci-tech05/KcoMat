/**
 * Boutons de partage (templates/partials/partage.html).
 * - « Partager » natif (téléphone) : envoie l'image + la description + le lien
 *   (ex. directement dans un statut ou une discussion WhatsApp).
 * - « Copier le lien » : copie dans le presse-papiers avec confirmation.
 */
(function () {
  'use strict';

  function fichierImage(url) {
    if (!url || !window.fetch) return Promise.resolve(null);
    return fetch(url, { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.blob() : null; })
      .then(function (blob) {
        if (!blob || !/^image\//.test(blob.type)) return null;
        var ext = blob.type.split('/')[1].replace('jpeg', 'jpg');
        return new File([blob], 'kcomat.' + ext, { type: blob.type });
      })
      .catch(function () { return null; });
  }

  function initBloc(bloc) {
    var titre = bloc.dataset.titre, texte = bloc.dataset.texte, url = bloc.dataset.url;
    var natif = bloc.querySelector('[data-partage-natif]');
    var copier = bloc.querySelector('[data-partage-copier]');
    var image = null;

    if (natif && navigator.share) {
      natif.hidden = false;
      // image préparée à l'avance : le partage doit partir directement du clic
      fichierImage(bloc.dataset.image).then(function (f) { image = f; });
      natif.addEventListener('click', function () {
        var message = titre + '\n' + texte + '\n\n' + url;
        var donnees = { title: titre, text: message };
        if (image && navigator.canShare && navigator.canShare({ files: [image] })) {
          donnees.files = [image];
        } else {
          donnees = { title: titre, text: titre + '\n' + texte, url: url };
        }
        navigator.share(donnees).catch(function () { /* partage annulé */ });
      });
    }

    if (copier) {
      var libelle = copier.querySelector('[data-partage-copier-texte]');
      copier.addEventListener('click', function () {
        var fini = function () {
          copier.classList.add('is-ok');
          if (libelle) libelle.textContent = 'Lien copié ✓';
          setTimeout(function () { copier.classList.remove('is-ok'); if (libelle) libelle.textContent = 'Copier le lien'; }, 2200);
        };
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(url).then(fini, function () { window.prompt('Copiez ce lien :', url); });
        } else {
          window.prompt('Copiez ce lien :', url);
        }
      });
    }
  }

  function demarrer() { document.querySelectorAll('[data-partage]').forEach(initBloc); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', demarrer);
  else demarrer();
})();
