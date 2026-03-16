import json
import logging
import subprocess
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def create_transaction(request):
    """Crée une transaction FedaPay via le script PHP bridge."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Données JSON invalides'}, status=400)

    required_fields = ['amount', 'description', 'currency', 'country', 'callback_url']
    for field in required_fields:
        if not data.get(field):
            return JsonResponse({'success': False, 'error': f'Champ requis manquant: {field}'}, status=400)

    php_script = Path(__file__).parent / 'create-transaction.php'
    if not php_script.exists():
        logger.error('PHP script not found: %s', php_script)
        return JsonResponse({'success': False, 'error': 'Script de paiement introuvable'}, status=500)

    # Transmettre la config FedaPay depuis Django vers le script PHP
    data['api_key'] = settings.FEDAPAY_CONFIG.get('api_key', '')
    data['environment'] = settings.FEDAPAY_CONFIG.get('environment', 'sandbox')

    try:
        payload = json.dumps(data).encode('utf-8')
        result = subprocess.run(
            ['php', str(php_script)],
            input=payload,
            capture_output=True,
            timeout=20,
        )

        stdout_text = result.stdout.decode('utf-8', errors='ignore').strip()
        stderr_text = result.stderr.decode('utf-8', errors='ignore').strip()

        if result.returncode != 0:
            logger.error('PHP error returncode=%s stderr=%s stdout=%s', result.returncode, stderr_text, stdout_text)
            return JsonResponse({'success': False, 'error': 'Erreur lors de la création de la transaction FedaPay'}, status=500)

        try:
            response_data = json.loads(stdout_text)
        except json.JSONDecodeError:
            logger.error('Invalid JSON from PHP. stdout=%s stderr=%s', stdout_text, stderr_text)
            return JsonResponse({'success': False, 'error': 'Réponse invalide du service de paiement'}, status=500)

        # Défense supplémentaire: s'assurer que token est toujours une string.
        token_value = response_data.get('token')
        if isinstance(token_value, dict):
            response_data['token'] = token_value.get('token') or token_value.get('jwt') or ''

        if response_data.get('success') and (not isinstance(response_data.get('token'), str) or not response_data.get('token')):
            logger.error('Invalid token format from PHP response: %s', response_data)
            return JsonResponse({'success': False, 'error': 'Token de paiement invalide'}, status=500)

        return JsonResponse(response_data)

    except subprocess.TimeoutExpired:
        logger.error('PHP script timeout')
        return JsonResponse({'success': False, 'error': 'Timeout lors de la création de la transaction'}, status=500)
    except Exception:
        logger.exception('Unexpected error while creating transaction')
        return JsonResponse({'success': False, 'error': 'Erreur interne lors de la création de la transaction'}, status=500)
