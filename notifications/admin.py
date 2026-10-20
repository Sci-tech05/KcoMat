from django.contrib import admin, messages
from django.utils.html import format_html

from .models import AbonnementPush, NotificationPush
from .push import notifier_publication, planifier, push_configure


def _oui_non(valeur):
    return format_html('<span style="color:{}">{}</span>', '#059669' if valeur else '#CBD5E1', '●')


@admin.register(AbonnementPush)
class AbonnementPushAdmin(admin.ModelAdmin):
    list_display = ['abonne', 'appareil', 'pref_offres', 'pref_formations', 'pref_projets', 'actif', 'created_at', 'dernier_envoi']
    list_filter = ['actif', 'offres', 'formations', 'projets', 'appareil']
    search_fields = ['utilisateur__username', 'utilisateur__email', 'appareil']
    readonly_fields = ['endpoint', 'p256dh', 'auth', 'utilisateur', 'appareil', 'echecs', 'created_at', 'dernier_envoi']
    fields = ['utilisateur', 'appareil', 'offres', 'formations', 'projets', 'actif', 'echecs', 'created_at', 'dernier_envoi', 'endpoint']
    actions = ['envoyer_test']

    def has_add_permission(self, request):
        return False   # les abonnements viennent des visiteurs (bouton « S'abonner »)

    @admin.display(description='Abonné', ordering='utilisateur__username')
    def abonne(self, obj):
        if obj.utilisateur_id:
            return format_html('<b>{}</b><br><span style="color:#64748B;font-size:.8rem">{}</span>',
                               obj.utilisateur.get_full_name() or obj.utilisateur.username, obj.utilisateur.email)
        return format_html('<span style="color:#64748B">Visiteur sans compte</span>')

    @admin.display(description='Offres')
    def pref_offres(self, obj):
        return _oui_non(obj.offres)

    @admin.display(description='Formations')
    def pref_formations(self, obj):
        return _oui_non(obj.formations)

    @admin.display(description='Projets')
    def pref_projets(self, obj):
        return _oui_non(obj.projets)

    @admin.action(description="Envoyer une notification de test")
    def envoyer_test(self, request, queryset):
        if not push_configure():
            self.message_user(request, "Clés VAPID manquantes : lancez « python manage.py generer_cles_vapid ».", messages.ERROR)
            return
        from .push import envoyer
        notification = NotificationPush.objects.create(
            type_notification='test', titre='Test KcoMat', url='/',
            message="Les notifications fonctionnent sur cet appareil.")
        envoyer(notification, abonnements=queryset)   # uniquement les appareils sélectionnés
        self.message_user(request, f"Test : {notification.envoyes} reçue(s), {notification.echecs} échec(s), "
                                   f"{notification.expires} abonnement(s) expiré(s) supprimé(s).",
                          messages.SUCCESS if notification.envoyes else messages.WARNING)


@admin.register(NotificationPush)
class NotificationPushAdmin(admin.ModelAdmin):
    list_display = ['titre', 'type_notification', 'resultat', 'created_at']
    list_filter = ['type_notification']
    search_fields = ['titre', 'message']
    fields = ['type_notification', 'titre', 'message', 'url', 'image', 'envoyes', 'echecs', 'expires', 'created_at']
    readonly_fields = ['envoyes', 'echecs', 'expires', 'created_at']

    def get_readonly_fields(self, request, obj=None):
        # une notification envoyée n'est plus modifiable (journal)
        return [f for f in self.fields] if obj else self.readonly_fields

    def has_change_permission(self, request, obj=None):
        return obj is None or super().has_change_permission(request, obj)

    @admin.display(description='Résultat')
    def resultat(self, obj):
        return format_html('<b style="color:#059669">{}</b> reçue(s) · <span style="color:#E11D48">{}</span> échec(s)',
                           obj.envoyes, obj.echecs)

    def save_model(self, request, obj, form, change):
        """« Ajouter une notification » = envoi immédiat d'une annonce à tous les abonnés concernés."""
        super().save_model(request, obj, form, change)
        if not change:
            if not push_configure():
                self.message_user(request, "Clés VAPID manquantes : notification enregistrée mais non envoyée.", messages.ERROR)
                return
            planifier(obj)
            self.message_user(request, "Notification en cours d'envoi aux abonnés. Rechargez cette liste dans "
                                       "quelques secondes pour voir le nombre de réceptions.", messages.SUCCESS)


@admin.action(description="Notifier les abonnés (nouvelle publication)")
def notifier_abonnes(modeladmin, request, queryset):
    """Action ajoutée aux offres, formations et projets : renvoie l'annonce aux abonnés."""
    n = 0
    for obj in queryset.filter(actif=True):
        if notifier_publication(obj, forcer=True):
            n += 1
    ignores = queryset.count() - n
    modeladmin.message_user(request, f"{n} annonce(s) envoyée(s) aux abonnés."
                            + (f" {ignores} élément(s) non publié(s) ignoré(s)." if ignores else ""),
                            messages.SUCCESS if n else messages.WARNING)

