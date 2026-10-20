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
