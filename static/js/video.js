/* Aperçus vidéo YouTube / TikTok : le lecteur n'est chargé qu'au clic (pages légères). */
(function () {
  'use strict';
  document.addEventListener('click', function (event) {
    var facade = event.target.closest('.vid__facade');
    if (!facade) return;
    var conteneur = facade.closest('.vid');
    if (!conteneur || conteneur.classList.contains('is-playing')) return;
    var iframe = document.createElement('iframe');
    iframe.src = conteneur.dataset.videoSrc;
    iframe.title = conteneur.dataset.videoTitle || 'Vidéo';
    iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share; fullscreen';
    iframe.allowFullscreen = true;
    iframe.referrerPolicy = 'strict-origin-when-cross-origin';
    iframe.className = 'vid__frame';
    conteneur.classList.add('is-playing');
    conteneur.appendChild(iframe);
    facade.hidden = true;
    iframe.focus();
  });
})();

/* Miniatures YouTube nettes : on charge la version HD (maxresdefault, 1280 px) ; si la vidéo n'en a pas,
   YouTube renvoie une image grise de 120 × 90 : on passe alors à sddefault (640 px), puis hqdefault. */
(function () {
  'use strict';
  function verifier(img) {
    if (!img.complete) return;                 // l'événement load/error rappellera cette fonction
    if (img.naturalWidth > 120) return;        // vraie miniature reçue
    var suivantes = (img.dataset.thumbFallback || '').split(' ').filter(Boolean);
    if (!suivantes.length) return;
    img.dataset.thumbFallback = suivantes.slice(1).join(' ');
    img.src = suivantes[0];
  }
  function surEvenement(event) {
    var img = event.target;
    if (img && img.tagName === 'IMG' && img.hasAttribute('data-thumb-fallback')) verifier(img);
  }
  document.addEventListener('load', surEvenement, true);   // load / error ne remontent pas : phase de capture
  document.addEventListener('error', surEvenement, true);
  function balayer() { document.querySelectorAll('img[data-thumb-fallback]').forEach(verifier); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', balayer); else balayer();
  window.addEventListener('load', balayer);
})();
