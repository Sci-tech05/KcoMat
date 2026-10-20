/**
 * Carrousels à défilement continu (accueil : services, réalisations, composants).
 *
 * Balisage :
 *   <div id="x" class="svc-track" data-carrousel data-vitesse="0.45" tabindex="0">
 *     … éléments originaux …
 *     … copies marquées data-clone hidden (2 jeux) …
 *   </div>
 *   <button data-carrousel-dir="1" aria-controls="x">
 *
 * Deux modes automatiques :
 *   - data-vitesse="0.45"   défilement continu (pixels par image) ;
 *   - data-intervalle="1500" avance d'une carte toutes les 1,5 s (pas à pas).
 *
 * - Boucle infinie seulement si les éléments dépassent la largeur visible ; sinon affichage simple centré.
 * - Pause au survol, au toucher et au focus ; glisser à la souris ; flèches et touches ← →.
 * - Aucune animation automatique si l'utilisateur préfère réduire les animations.
 */
(function () {
  'use strict';
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function boutons(track) {
    return document.querySelectorAll('[data-carrousel-dir][aria-controls="' + track.id + '"]');
  }

  function initialiser(track) {
    var originaux = Array.prototype.filter.call(track.children, function (el) { return !el.hasAttribute('data-clone'); });
    var clones = track.querySelectorAll('[data-clone]');
    var gap = parseFloat(getComputedStyle(track).columnGap) || 20;
    var largeurOriginaux = originaux.reduce(function (somme, el) { return somme + el.getBoundingClientRect().width + gap; }, 0);

    // Pas assez d'éléments pour remplir la largeur : affichage simple, sans boucle
    if (!originaux.length || largeurOriginaux <= track.clientWidth + 1) {
      clones.forEach(function (el) { el.remove(); });
      track.classList.add('is-static');
      boutons(track).forEach(function (b) { b.hidden = true; });
      return;
    }
    clones.forEach(function (el) { el.hidden = false; });

    var COPIES = 3;
    var vitesse = parseFloat(track.dataset.vitesse || '0.45');
    var intervalle = parseInt(track.dataset.intervalle || '0', 10);
    var enPause = false, minuteur = null, pos = 0;

    // largeur exacte d'un jeu de cartes : écart entre la 1re carte et sa 1re copie
    function largeurJeu() {
      return clones.length ? clones[0].offsetLeft - originaux[0].offsetLeft : track.scrollWidth / COPIES;
    }
    // garde la position dans la copie du milieu : boucle dans les deux sens
    function normaliser(x) {
      var w = largeurJeu();
      while (x < w) x += w;
      while (x >= 2 * w) x -= w;
      return x;
    }
    pos = normaliser(largeurJeu());
    track.scrollLeft = pos;
    window.addEventListener('resize', function () { pos = normaliser(track.scrollLeft); track.scrollLeft = pos; });

    function pause() { enPause = true; clearTimeout(minuteur); }
    function reprendre(delai) {
      clearTimeout(minuteur);
      minuteur = setTimeout(function () {
        pos = normaliser(track.scrollLeft); track.scrollLeft = pos; enPause = false;
      }, delai || 1500);
    }
    function boucle() {
      if (!enPause && !document.hidden) {
        pos = normaliser(pos + vitesse);
        track.scrollLeft = pos;
      }
      requestAnimationFrame(boucle);
    }

    track.addEventListener('mouseenter', pause);
    track.addEventListener('mouseleave', function () { if (!glisse) reprendre(400); });
    track.addEventListener('focusin', pause);
    track.addEventListener('focusout', function () { reprendre(800); });
    track.addEventListener('touchstart', pause, { passive: true });
    track.addEventListener('touchend', function () { reprendre(2500); }, { passive: true });
    track.addEventListener('wheel', function () { pause(); reprendre(2000); }, { passive: true });
    track.addEventListener('dragstart', function (e) { e.preventDefault(); });

    // Glisser à la souris (sans ouvrir le lien en fin de glisser)
    var glisse = false, deplace = false, departX = 0, departScroll = 0;
    track.addEventListener('pointerdown', function (e) {
      if (e.pointerType !== 'mouse' || e.button !== 0) return;
      glisse = true; deplace = false; departX = e.clientX; departScroll = track.scrollLeft;
      pause();
    });
    window.addEventListener('pointermove', function (e) {
      if (!glisse) return;
      // Le mode « glisser » (qui neutralise les liens) ne démarre qu'après un vrai déplacement :
      // un simple clic doit toujours ouvrir la carte.
      if (!deplace && Math.abs(e.clientX - departX) > 5) {
        deplace = true;
        track.classList.add('is-dragging');
      }
      if (deplace) track.scrollLeft = departScroll - (e.clientX - departX);
    });
    window.addEventListener('pointerup', function () {
      if (!glisse) return;
      glisse = false; track.classList.remove('is-dragging');
      pos = normaliser(track.scrollLeft); track.scrollLeft = pos;
      if (!track.matches(':hover')) reprendre(1200);
    });
    track.addEventListener('click', function (e) { if (deplace) { e.preventDefault(); deplace = false; } }, true);

    function largeurPas() {
      var element = originaux[0];
      return element ? element.getBoundingClientRect().width + gap : 320;
    }
    function glisserDe(sens) {
      pos = normaliser(track.scrollLeft); track.scrollLeft = pos;
      // s'aligne sur le début de la carte suivante (ou précédente)
      var pas = largeurPas();
      var cible = (Math.round(pos / pas) + sens) * pas;
      pos = cible;
      track.scrollTo({ left: cible, behavior: reduce ? 'auto' : 'smooth' });
    }
    function aller(sens) {
      pause();
      glisserDe(sens);
      reprendre(2600);
    }
    boutons(track).forEach(function (bouton) {
      bouton.addEventListener('click', function () { aller(Number(bouton.dataset.carrouselDir)); });
    });
    track.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight') { e.preventDefault(); aller(1); }
      if (e.key === 'ArrowLeft') { e.preventDefault(); aller(-1); }
    });

    if (reduce) return;
    if (intervalle > 0) {
      setInterval(function () { if (!enPause && !document.hidden) glisserDe(1); }, intervalle);
    } else {
      requestAnimationFrame(boucle);
    }
  }

  function demarrer() {
    document.querySelectorAll('[data-carrousel]').forEach(initialiser);
  }
  // Les largeurs des cartes sont fixées en CSS : inutile d'attendre les images (script chargé en defer).
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', demarrer);
  else demarrer();
})();
