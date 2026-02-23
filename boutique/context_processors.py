from .models import Panier


def cart_context(request):
    """Injecte le nombre d'articles dans le panier pour tous les templates."""
    count = 0
    try:
        if request.user.is_authenticated:
            panier = Panier.objects.filter(utilisateur=request.user).first()
        else:
            session_key = request.session.session_key
            if session_key:
                panier = Panier.objects.filter(session_key=session_key).first()
            else:
                panier = None
        if panier:
            count = panier.nombre_articles()
    except Exception:
        pass
    return {'cart_count': count}
