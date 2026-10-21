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

    // Onglets sur une ligne défilante : fondu sur le bord qui cache des onglets,
    // et l'onglet actif est ramené dans la zone visible.
    function initTabsScroll() {
        var bar = document.querySelector('ul#jazzy-tabs');
        if (!bar) return;
        function maj() {
            var max = bar.scrollWidth - bar.clientWidth;
            bar.classList.toggle('kx-more-left', bar.scrollLeft > 4);
            bar.classList.toggle('kx-more-right', max - bar.scrollLeft > 4);
        }
        function montrerActif() {
            var actif = bar.querySelector('.nav-link.active');
            if (!actif) return;
            var item = actif.parentElement;
            var gauche = item.offsetLeft - bar.offsetLeft;
            if (gauche < bar.scrollLeft || gauche + item.offsetWidth > bar.scrollLeft + bar.clientWidth) {
                bar.scrollTo({ left: Math.max(0, gauche - 24), behavior: 'smooth' });
            }
        }
        bar.addEventListener('scroll', maj, { passive: true });
        window.addEventListener('resize', maj);
        bar.addEventListener('click', function () { setTimeout(function () { montrerActif(); maj(); }, 50); });
        montrerActif();
        maj();
    }

    // Barre latérale : garde sa position de défilement d'une page à l'autre
    // (exécuté tout de suite, avant le premier affichage, pour éviter tout saut).
    function initSidebarScroll() {
        var CLE = 'kx-sidebar-scroll';
        // Jazzmin fait défiler l'élément #jazzy-sidebar (et non .sidebar)
        var barre = document.getElementById('jazzy-sidebar') || document.querySelector('.main-sidebar');
        if (!barre) return;
        function restaurer() {
            var memo = null;
            try { memo = sessionStorage.getItem(CLE); } catch (e) { /* stockage indisponible */ }
            if (memo !== null) {
                barre.scrollTop = parseInt(memo, 10) || 0;
            }
            // lien actif hors de la zone visible (première visite, lien ouvert depuis ailleurs) : on le ramène au centre
            var actif = barre.querySelector('.nav-link.active');
            if (actif) {
                var r = actif.getBoundingClientRect(), b = barre.getBoundingClientRect();
                if (r.top < b.top + 60 || r.bottom > b.bottom - 20) {
                    barre.scrollTop += r.top - b.top - (barre.clientHeight - r.height) / 2;
                }
            }
        }
        restaurer();
        // page préchargée en arrière-plan : on relit la position au moment où elle s'affiche vraiment
        if (document.prerendering) {
            document.addEventListener('prerenderingchange', restaurer, { once: true });
        }
        function sauver() {
            if (document.prerendering) return;   // une page encore invisible ne doit rien écraser
            try { sessionStorage.setItem(CLE, String(Math.round(barre.scrollTop))); } catch (e) { /* ignoré */ }
        }
        var attente = null;
        barre.addEventListener('scroll', function () { clearTimeout(attente); attente = setTimeout(sauver, 120); }, { passive: true });
        window.addEventListener('pagehide', sauver);
        barre.addEventListener('click', sauver, true);
    }

    // Préchargement des pages de la barre latérale : la page suivante est prête
    // avant même le clic (survol à la souris, appui au doigt).
    function initPrechargement() {
        var liens = '.nav-sidebar a.nav-link[href^="/"]:not([href*="logout"])';
        if (window.HTMLScriptElement && HTMLScriptElement.supports && HTMLScriptElement.supports('speculationrules')) {
            var regles = document.createElement('script');
            regles.type = 'speculationrules';
            regles.textContent = JSON.stringify({
                prerender: [{ source: 'document', where: { selector_matches: liens }, eagerness: 'moderate' }]
            });
            document.head.appendChild(regles);
            return;
        }
        var faits = {};
        function prefetch(e) {
            var a = e.target.closest && e.target.closest(liens);
            if (!a || faits[a.href] || a.href === location.href) return;
            faits[a.href] = true;
            var l = document.createElement('link');
            l.rel = 'prefetch'; l.href = a.href;
            document.head.appendChild(l);
        }
        document.addEventListener('mouseover', prefetch, { passive: true });
        document.addEventListener('touchstart', prefetch, { passive: true });
    }

    document.documentElement.classList.add('kx-preload');
    initSidebarScroll();
    window.addEventListener('load', function () {
        requestAnimationFrame(function () { document.documentElement.classList.remove('kx-preload'); });
    });

    document.addEventListener('DOMContentLoaded', function () {
        initPrechargement();
        initTabsHash();
        initUserMenuFallback();
        initFilePreviews();
        initTabsScroll();
    });
})();
