/**
 * Colonnes « collantes » (pages de détail, contact, profil, panier) — sur PC.
 *
 * Balisage : <div class="grid lg:grid-cols-3 …" data-colonnes> <colonne/> <colonne/> </div>
 *
 * Quand les colonnes sont côte à côte, la plus courte suit le défilement :
 * - si elle tient dans l'écran, elle reste fixée sous l'en-tête ;
 * - sinon, elle défile normalement puis se fixe quand son bas atteint le bas de l'écran.
 * Ainsi, on ne voit jamais un grand vide sous la colonne la plus courte.
 */
(function () {
  'use strict';
  var HAUT = 96;   // hauteur de l'en-tête fixe + marge
  var BAS = 24;

  function reinitialiser(col) {
    col.style.position = ''; col.style.top = '';
    col.classList.remove('is-collante');
  }

  function ajuster(grille) {
    var colonnes = Array.prototype.filter.call(grille.children, function (el) {
      return el.offsetParent !== null && !el.hidden;
    });
    colonnes.forEach(reinitialiser);
    if (colonnes.length < 2) return;
    // Colonnes empilées (téléphone, tablette) : rien à faire
    // offsetTop ignore les animations d'apparition (transform) en cours
    var cotes = Math.abs(colonnes[0].offsetTop - colonnes[1].offsetTop) < 2;
    if (!cotes || window.innerWidth < 1024) {
      colonnes.forEach(function (col) { col.style.alignSelf = ''; });
      return;
    }
    // hauteur réelle de chaque colonne (sans l'étirement de la grille)
    colonnes.forEach(function (col) { col.style.alignSelf = 'start'; });
    var plusHaute = Math.max.apply(null, colonnes.map(function (c) { return c.offsetHeight; }));
    colonnes.forEach(function (col) {
      var h = col.offsetHeight;
      if (h >= plusHaute - 40) return;   // la colonne la plus longue défile normalement
      var top = h + HAUT + BAS <= window.innerHeight ? HAUT : window.innerHeight - h - BAS;
      col.style.position = 'sticky';
      col.style.top = top + 'px';
      col.classList.add('is-collante');
    });
  }

  function demarrer() {
    var grilles = document.querySelectorAll('[data-colonnes]');
    if (!grilles.length) return;
    var enAttente = false;
    function tout() {
      if (enAttente) return;
      enAttente = true;
      requestAnimationFrame(function () { enAttente = false; grilles.forEach(ajuster); });
    }
    tout();
    window.addEventListener('resize', tout);
    window.addEventListener('load', tout);
    if ('ResizeObserver' in window) {
      var obs = new ResizeObserver(tout);
      grilles.forEach(function (g) { Array.prototype.forEach.call(g.children, function (c) { obs.observe(c); }); });
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', demarrer);
  else demarrer();
})();
