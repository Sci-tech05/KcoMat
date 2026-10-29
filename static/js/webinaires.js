/* Webinaires : comptes à rebours et bascule automatique des boutons.
 *
 *   <div data-wb-countdown data-cible="1730970000" data-bascule="1730969400"> … [data-u="j|h|m|s"] … </div>
 *   <body … data-wb-now="1730960000">   (heure du serveur, corrige une horloge locale décalée)
 *
 * data-cible   : instant affiché (début, ou fin pendant le direct), en secondes Unix
 * data-bascule : instant où l'état change (ouverture de la salle 10 min avant, début, fin) ; la page se recharge
 *                alors pour afficher le bon bouton (« Participer », « Télécharger mon attestation »…).
 */
(function () {
  'use strict';
  var compteurs = document.querySelectorAll('[data-wb-countdown]');
  if (!compteurs.length) return;

  var repere = document.querySelector('[data-wb-now]');
  var decalage = repere ? parseInt(repere.getAttribute('data-wb-now'), 10) * 1000 - Date.now() : 0;
  var chargement = Date.now() + decalage;
  var rechargement = false;

  function deux(n) { return (n < 10 ? '0' : '') + n; }

  function ecrire(el, unite, valeur) {
    var cible = el.querySelector('[data-u="' + unite + '"]');
    if (cible && cible.textContent !== String(valeur)) cible.textContent = valeur;
  }

  function tic() {
    var maintenant = Date.now() + decalage;
    compteurs.forEach(function (el) {
      var cible = parseInt(el.getAttribute('data-cible'), 10) * 1000;
      var bascule = parseInt(el.getAttribute('data-bascule') || '0', 10) * 1000;
      var reste = Math.max(0, Math.floor((cible - maintenant) / 1000));
      ecrire(el, 'j', Math.floor(reste / 86400));
      ecrire(el, 'h', deux(Math.floor((reste % 86400) / 3600)));
      ecrire(el, 'm', deux(Math.floor((reste % 3600) / 60)));
      ecrire(el, 's', deux(reste % 60));
      var texte = el.querySelector('[data-u="texte"]');
      if (texte) {
        var j = Math.floor(reste / 86400), h = Math.floor((reste % 86400) / 3600), m = Math.floor((reste % 3600) / 60);
        texte.textContent = j ? j + ' j ' + deux(h) + ' h' : (h ? h + ' h ' + deux(m) + ' min' : m + ' min ' + deux(reste % 60) + ' s');
      }
      // ne recharge que pour une bascule survenue pendant que la page est ouverte (pas de boucle)
      if (bascule && !rechargement && bascule > chargement && maintenant >= bascule) {
        rechargement = true;
        setTimeout(function () { window.location.reload(); }, 1200);
      }
    });
  }

  tic();
  setInterval(tic, 1000);
})();
