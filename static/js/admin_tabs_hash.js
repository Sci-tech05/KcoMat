/**
 * admin_tabs_hash.js
 * Active l'onglet Jazzmin correspondant au hash de l'URL.
 * Jazzmin utilise data-toggle="pill" (Bootstrap 4 / AdminLTE 3).
 */
(function ($) {
    $(document).ready(function () {

        function findTabLink(hash) {
            if (!hash) return $();
            var decoded = decodeURIComponent(hash);
            return $('[data-toggle="pill"][href="' + decoded + '"],' +
                '[data-toggle="pill"][href="' + hash + '"],' +
                '[data-toggle="tab"][href="' + decoded + '"],' +
                '[data-toggle="tab"][href="' + hash + '"]').first();
        }

        function activateTabFromHash() {
            var $link = findTabLink(window.location.hash);
            if ($link.length) {
                $link.tab('show');
            }
        }

        // Au chargement : attendre que AdminLTE finisse son init (peut dépasser 50ms)
        // On tente à 100ms, 300ms et 600ms pour couvrir tous les cas
        setTimeout(activateTabFromHash, 100);
        setTimeout(activateTabFromHash, 300);
        setTimeout(activateTabFromHash, 600);

        // Navigation via hashchange (liens internes, bouton précédent/suivant)
        $(window).on('hashchange', function () {
            activateTabFromHash();
        });

        // Mettre à jour le hash quand on clique sur un onglet
        $(document).on('shown.bs.tab', '[data-toggle="pill"], [data-toggle="tab"]', function (e) {
            history.replaceState(null, null, $(e.target).attr('href'));
        });

    });
})(jQuery);
