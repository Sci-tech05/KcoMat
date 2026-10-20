/**
 * admin_premium.js (chargé via JAZZMIN_SETTINGS['custom_js'])
 * - Active l'onglet Jazzmin correspondant au hash de l'URL.
 * - Ajoute un fallback pour le menu utilisateur (avatar) si le dropdown Bootstrap ne se declenche pas.
 * - Affiche l'aperçu des images (fichier actuel et nouveau fichier choisi) dans les formulaires.
 */
(function () {
    function initTabsHash() {
        if (typeof window.jQuery === 'undefined') {
            return;
        }

        var $ = window.jQuery;

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
            if (!$link.length) {
                return;
            }

            if (typeof $link.tab === 'function') {
                $link.tab('show');
                return;
            }

            var href = $link.attr('href');
            if (!href || href.charAt(0) !== '#') {
                return;
            }
            var pane = document.querySelector(href);
            if (pane) {
                pane.classList.add('active', 'show');
            }
            $link.addClass('active');
        }

        setTimeout(activateTabFromHash, 100);
        setTimeout(activateTabFromHash, 300);
        setTimeout(activateTabFromHash, 600);

        $(window).on('hashchange', function () {
            activateTabFromHash();
        });

        $(document).on('shown.bs.tab', '[data-toggle="pill"], [data-toggle="tab"]', function (e) {
            history.replaceState(null, null, $(e.target).attr('href'));
        });
    }

    function initUserMenuFallback() {
        var selectors = [
            '.user-menu .dropdown-toggle',
            '.user-menu [data-toggle="dropdown"]',
            '.user-menu [data-bs-toggle="dropdown"]',
            '.navbar .dropdown.user-menu > a',
            '.navbar .nav-item.dropdown > .nav-link[data-toggle="dropdown"]',
            '.navbar .nav-item.dropdown > .nav-link[data-bs-toggle="dropdown"]',
            '.navbar .dropdown > .dropdown-toggle',
        ];

        function closeAllMenus() {
            document.querySelectorAll('.navbar .dropdown-menu.show').forEach(function (menu) {
                menu.classList.remove('show');
                var toggle = menu.parentElement ? menu.parentElement.querySelector('.dropdown-toggle') : null;
                if (toggle) {
                    toggle.setAttribute('aria-expanded', 'false');
                }
            });
        }

        document.addEventListener('click', function (event) {
            var toggle = event.target.closest(selectors.join(','));
            if (!toggle) {
                if (!event.target.closest('.navbar .dropdown-menu')) {
                    closeAllMenus();
                }
                return;
            }

            var parent = toggle.closest('.dropdown');
            if (!parent) {
                return;
            }

            var menu = parent.querySelector('.dropdown-menu');
            if (!menu) {
                return;
            }

            // Si Bootstrap ne gere pas le dropdown, on force un fallback sans navigation.
            setTimeout(function () {
                if (menu.classList.contains('show')) {
                    return;
                }

                event.preventDefault();
                closeAllMenus();
                menu.classList.add('show');
                toggle.setAttribute('aria-expanded', 'true');
            }, 0);
        });

        // Sur certains themes admin, le lien user a href="#" et ne fait rien:
        // on bloque la navigation pour garder l'ouverture du menu en JS.
        document.addEventListener('click', function (event) {
            var toggle = event.target.closest(selectors.join(','));
            if (!toggle) {
                return;
            }

            var href = (toggle.getAttribute('href') || '').trim();
            if (!href || href === '#') {
                event.preventDefault();
            }
        }, true);
    }

    function initFilePreviews() {
        var IMAGE = /\.(jpe?g|png|webp|gif|avif)$/i;

        function previewFor(container) {
            var img = container.querySelector('.kx-file-preview');
            if (!img) {
                img = document.createElement('img');
                img.className = 'kx-file-preview';
                img.alt = '';
                container.insertBefore(img, container.firstChild);
            }
            return img;
        }

        document.querySelectorAll('input[type="file"]').forEach(function (input) {
            var container = input.closest('p.file-upload') || input.parentElement;
            var current = container.querySelector('a[href]');
            if (current && IMAGE.test(current.getAttribute('href').split('?')[0])) {
                previewFor(container).src = current.href;
            }
            input.addEventListener('change', function () {
                var file = input.files && input.files[0];
                if (!file || !/^image\//.test(file.type)) {
                    return;
                }
                var img = previewFor(container);
                if (img.dataset.objectUrl) {
                    URL.revokeObjectURL(img.dataset.objectUrl);
                }
                img.dataset.objectUrl = URL.createObjectURL(file);
                img.src = img.dataset.objectUrl;
            });
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        initTabsHash();
        initUserMenuFallback();
        initFilePreviews();
    });
})();
