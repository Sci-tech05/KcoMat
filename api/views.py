import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .fedapay_service import create_fedapay_transaction


@csrf_exempt
@require_http_methods(["POST"])
def create_transaction(request):
    """Cree une transaction FedaPay via l'API REST."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Donnees JSON invalides"}, status=400)

    required_fields = ["amount", "description", "currency", "country", "callback_url"]
    for field in required_fields:
        if not data.get(field):
            return JsonResponse({"success": False, "error": f"Champ requis manquant: {field}"}, status=400)

    result = create_fedapay_transaction(data)
    status_code = int(result.get("status_code", 500))
    payload = {key: value for key, value in result.items() if key != "status_code"}
    return JsonResponse(payload, status=status_code)
