/**
 * Panier sans rechargement : retrait d'un article et changement de quantité.
 * Sans JavaScript, les formulaires fonctionnent normalement (rechargement de page).
 */
(function () {
  'use strict';
  var formatter = new Intl.NumberFormat('fr-FR');

  function fcfa(valeur) {
    return formatter.format(valeur).replace(/ | /g, ' ');
  }

  function envoyer(form) {
    return fetch(form.action, {
      method: 'POST',
      body: new FormData(form),
      headers: { 'X-Requested-With': 'fetch', Accept: 'application/json' },
      credentials: 'same-origin',
    }).then(function (reponse) {
      if (!reponse.ok) throw new Error('HTTP ' + reponse.status);
      return reponse.json();
    });
  }

  function majTotaux(data) {
    document.querySelectorAll('[data-cart-total]').forEach(function (el) { el.textContent = fcfa(data.total); });
    var n = data.nombre_articles;
    document.querySelectorAll('[data-cart-count]').forEach(function (el) {
      el.textContent = n + ' article' + (n > 1 ? 's' : '') + ' sélectionné' + (n > 1 ? 's' : '');
      el.hidden = data.vide;
    });
    // pastille du menu (templates/base.html)
    var badge = document.getElementById('cart-badge');
    if (badge) {
      badge.textContent = n > 0 ? n : '';
      badge.className = n > 0
        ? 'absolute -top-1 -right-1 w-5 h-5 bg-blue-600 text-white text-xs rounded-full flex items-center justify-center font-bold'
        : '';
    }
    if (data.vide) {
      var plein = document.querySelector('[data-cart-filled]');
      var vide = document.querySelector('[data-cart-empty]');
      if (plein) plein.hidden = true;
      if (vide) vide.hidden = false;
    }
  }

  function retirerLigne(id) {
    var carte = document.querySelector('[data-cart-item="' + id + '"]');
    var ligne = document.querySelector('[data-cart-line="' + id + '"]');
    if (ligne) ligne.remove();
    if (!carte) return Promise.resolve();
    carte.style.height = carte.offsetHeight + 'px';
    carte.classList.add('is-removing');
    return new Promise(function (resolve) {
      setTimeout(function () { carte.remove(); resolve(); }, 320);
    });
  }

  function erreur(carte) {
    if (carte) {
      carte.classList.remove('is-busy', 'is-removing');
      carte.style.height = '';
    }
    window.alert("L'opération n'a pas pu aboutir. Vérifiez votre connexion et réessayez.");
  }

  // Retirer un article
  document.addEventListener('submit', function (event) {
    var form = event.target.closest('[data-cart-remove]');
    if (!form) return;
    event.preventDefault();
    var carte = form.closest('[data-cart-item]');
    if (!carte || carte.classList.contains('is-busy')) return;
    carte.classList.add('is-busy');
    envoyer(form)
      .then(function (data) {
        return retirerLigne(carte.dataset.cartItem).then(function () { majTotaux(data); });
      })
      .catch(function () { erreur(carte); });
  });

  // Changer la quantité (boutons − / + et saisie)
  var minuteurs = new WeakMap();

  function envoyerQuantite(form) {
    var carte = form.closest('[data-cart-item]');
    carte.classList.add('is-busy');
    envoyer(form)
      .then(function (data) {
        carte.classList.remove('is-busy');
        var id = carte.dataset.cartItem;
        if (data.item && data.item.supprime) {
          return retirerLigne(id).then(function () { majTotaux(data); });
        }
        form.querySelector('input[name=quantite]').value = data.item.quantite;
        var sousTotal = carte.querySelector('[data-cart-subtotal]');
        if (sousTotal) sousTotal.textContent = fcfa(data.item.sous_total);
        var ligne = document.querySelector('[data-cart-line="' + id + '"]');
        if (ligne) {
          ligne.querySelector('[data-cart-line-qty]').textContent = data.item.quantite;
          ligne.querySelector('[data-cart-line-subtotal]').textContent = fcfa(data.item.sous_total);
        }
        majTotaux(data);
      })
      .catch(function () { erreur(carte); });
  }

  function planifier(form) {
    clearTimeout(minuteurs.get(form));
    minuteurs.set(form, setTimeout(function () { envoyerQuantite(form); }, 350));   // regroupe les clics rapides
  }

  document.addEventListener('click', function (event) {
    var bouton = event.target.closest('[data-cart-qty] [data-step]');
    if (!bouton) return;
    var form = bouton.closest('[data-cart-qty]');
    var input = form.querySelector('input[name=quantite]');
    var max = parseInt(input.max, 10) || 999;
    var valeur = Math.min(max, Math.max(1, (parseInt(input.value, 10) || 1) + parseInt(bouton.dataset.step, 10)));
    if (String(valeur) === input.value) return;
    input.value = valeur;
    planifier(form);
  });

  document.addEventListener('change', function (event) {
    var input = event.target.closest('[data-cart-qty] input[name=quantite]');
    if (input) planifier(input.form);
  });

  document.addEventListener('submit', function (event) {
    var form = event.target.closest('[data-cart-qty]');
    if (!form) return;
    event.preventDefault();
    planifier(form);
  });
})();
