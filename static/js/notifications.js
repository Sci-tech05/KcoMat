/**
 * Notifications push KcoMat : abonnement, préférences, désabonnement.
 * Fenêtre : templates/notifications/_modal.html · Service worker : /sw.js
 */
(function () {
  'use strict';
  var config = document.getElementById('push-config');
  var modal = document.getElementById('push-modal');
  if (!config || !modal) return;

  var supported = 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
  var isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  var standalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
  var abonne = false;
  var dernierFocus = null;

  function csrfToken() {
    var input = modal.querySelector('input[name=csrfmiddlewaretoken]');
    return input ? input.value : '';
  }

  function cleVapid(valeur) {
    var padding = '='.repeat((4 - (valeur.length % 4)) % 4);
    var brut = window.atob((valeur + padding).replace(/-/g, '+').replace(/_/g, '/'));
    var tableau = new Uint8Array(brut.length);
    for (var i = 0; i < brut.length; i++) tableau[i] = brut.charCodeAt(i);
    return tableau;
  }

  function post(url, data) {
    return fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
      credentials: 'same-origin',
      body: JSON.stringify(data),
    }).then(function (r) { return r.json().then(function (json) { if (!r.ok) throw new Error(json.error || 'Erreur serveur'); return json; }); });
  }

  function preferences() {
    var prefs = {};
    // Les cases existent dans deux vues (« choisir » et « gérer ») : on lit celles de la vue affichée.
    modal.querySelectorAll('[data-push-view]:not([hidden]) [data-push-pref]').forEach(function (input) {
      prefs[input.dataset.pushPref] = input.checked;
    });
    return prefs;
  }

  function restaurerPreferences() {
    try {
      var prefs = JSON.parse(localStorage.getItem('kcomat-push-prefs') || 'null');
      if (prefs) modal.querySelectorAll('[data-push-pref]').forEach(function (input) {
        if (input.dataset.pushPref in prefs) input.checked = !!prefs[input.dataset.pushPref];
      });
    } catch (e) { /* stockage indisponible */ }
  }

  function memoriserPreferences(prefs) {
    try { localStorage.setItem('kcomat-push-prefs', JSON.stringify(prefs)); } catch (e) { /* ignore */ }
  }

  function afficherEtat(estAbonne) {
    abonne = estAbonne;
    document.documentElement.dataset.push = estAbonne ? 'on' : 'off';
    document.querySelectorAll('[data-push-label]').forEach(function (el) {
      el.textContent = estAbonne ? el.dataset.labelOn : el.dataset.labelOff;
    });
  }

  function vue(nom) {
    modal.querySelectorAll('[data-push-view]').forEach(function (el) { el.hidden = el.dataset.pushView !== nom; });
    var erreur = modal.querySelector('[data-push-error]');
    if (erreur) erreur.hidden = true;
  }

  function erreur(message) {
    var el = modal.querySelector('[data-push-error]');
    if (!el) return;
    el.textContent = message;
    el.hidden = false;
  }

  function occupe(bouton, actif, texte) {
    if (!bouton) return;
    bouton.disabled = actif;
    bouton.classList.toggle('is-busy', actif);
    if (actif && texte) {
      bouton.dataset.texteInitial = bouton.innerHTML;
      bouton.textContent = texte;
    } else if (!actif && bouton.dataset.texteInitial) {
      bouton.innerHTML = bouton.dataset.texteInitial;
      delete bouton.dataset.texteInitial;
    }
  }

  function abonnementActuel() {
    if (!supported) return Promise.resolve(null);
    return navigator.serviceWorker.getRegistration('/').then(function (reg) {
      return reg ? reg.pushManager.getSubscription() : null;
    });
  }

  function ouvrir() {
    dernierFocus = document.activeElement;
    restaurerPreferences();
    if (!supported) {
      vue(isIOS && !standalone ? 'ios' : 'unsupported');
    } else if (Notification.permission === 'denied') {
      vue('denied');
    } else {
      vue(abonne ? 'manage' : 'choose');
    }
    modal.hidden = false;
    document.body.classList.add('overflow-hidden');
    var cible = modal.querySelector('[data-push-view]:not([hidden]) [data-autofocus]') || modal.querySelector('[data-push-close]');
    if (cible) setTimeout(function () { cible.focus(); }, 30);
  }

  function fermer() {
    modal.hidden = true;
    document.body.classList.remove('overflow-hidden');
    if (dernierFocus && dernierFocus.focus) dernierFocus.focus();
  }

  function sAbonner(bouton) {
    var prefs = preferences();
    if (!prefs.offres && !prefs.formations && !prefs.projets && !prefs.webinaires) {
      erreur('Choisissez au moins un type de notification.');
      return;
    }
    occupe(bouton, true, 'Activation en cours…');
    Notification.requestPermission()
      .then(function (permission) {
        if (permission !== 'granted') { vue('denied'); throw null; }
        return navigator.serviceWorker.register('/sw.js', { scope: '/' });
      })
      .then(function () { return navigator.serviceWorker.ready; })
      .then(function (reg) {
        var abonnement = reg.pushManager.getSubscription().then(function (existant) {
          return existant || reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: cleVapid(config.dataset.vapid) });
        });
        // Le service push du navigateur peut ne pas répondre (réseau lent) : on ne laisse pas le visiteur attendre indéfiniment.
        var delai = new Promise(function (_, rejeter) {
          setTimeout(function () { rejeter(new Error('timeout')); }, 45000);   // 1re inscription parfois lente
        });
        return Promise.race([abonnement, delai]);
      })
      .then(function (subscription) {
        return post(config.dataset.subscribeUrl, { subscription: subscription.toJSON(), preferences: prefs });
      })
      .then(function () {
        memoriserPreferences(prefs);
        afficherEtat(true);
        vue('done');
      })
      .catch(function (e) {
        if (e && e.message === 'timeout') erreur("Le service de notifications de votre navigateur ne répond pas. Vérifiez votre connexion internet et réessayez.");
        else if (e) erreur("L'abonnement n'a pas abouti. Vérifiez votre connexion et réessayez.");
      })
      .finally(function () { occupe(bouton, false); });
  }

  function enregistrerPreferences(bouton) {
    var prefs = preferences();
    if (!prefs.offres && !prefs.formations && !prefs.projets && !prefs.webinaires) {
      erreur('Choisissez au moins un type de notification, ou désabonnez-vous.');
      return;
    }
    occupe(bouton, true);
    abonnementActuel()
      .then(function (subscription) {
        if (!subscription) throw new Error();
        return post(config.dataset.subscribeUrl, { subscription: subscription.toJSON(), preferences: prefs });
      })
      .then(function () { memoriserPreferences(prefs); vue('saved'); })
      .catch(function () { erreur("Impossible d'enregistrer vos préférences pour le moment."); })
      .finally(function () { occupe(bouton, false); });
  }

  function seDesabonner(bouton) {
    occupe(bouton, true);
    abonnementActuel()
      .then(function (subscription) {
        if (!subscription) return null;
        return post(config.dataset.unsubscribeUrl, { endpoint: subscription.endpoint })
          .catch(function () { return null; })
          .then(function () { return subscription.unsubscribe(); });
      })
      .then(function () { afficherEtat(false); vue('bye'); })
      .catch(function () { erreur('Le désabonnement a échoué. Réessayez.'); })
      .finally(function () { occupe(bouton, false); });
  }

  document.addEventListener('click', function (event) {
    var cible = event.target.closest('[data-push-open], [data-push-close], [data-push-action]');
    if (!cible) {
      if (event.target === modal.querySelector('[data-push-backdrop]')) fermer();
      return;
    }
    if (cible.hasAttribute('data-push-open')) { event.preventDefault(); ouvrir(); return; }
    if (cible.hasAttribute('data-push-close')) { event.preventDefault(); fermer(); return; }
    var action = cible.dataset.pushAction;
    if (action === 'subscribe') sAbonner(cible);
    else if (action === 'save') enregistrerPreferences(cible);
    else if (action === 'unsubscribe') seDesabonner(cible);
    else if (action === 'manage') vue('manage');
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && !modal.hidden) fermer();
  });

  // État initial (bouton « S'abonner » clignotant tant que non abonné)
  abonnementActuel().then(function (subscription) { afficherEtat(!!subscription); }).catch(function () { afficherEtat(false); })
    .then(function () {
      if (config.dataset.autoOpen === '1' && !abonne) setTimeout(ouvrir, 1200);   // juste après la création de compte
    });
})();
