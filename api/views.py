import json
import logging
from typing import Any

import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)


def _fedapay_base_url(environment: str) -> str:
    env = (environment or '').strip().lower()
    if env == 'sandbox':
        return 'https://sandbox-api.fedapay.com/v1'
    return 'https://api.fedapay.com/v1'


def _extract_error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = {}

    if isinstance(payload, dict):
        for key in ('message', 'error', 'detail'):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return f"Erreur HTTP FedaPay ({response.status_code})"


def _build_transaction_payload(data: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        'amount': int(data['amount']),
        'description': data['description'],
        'currency': {'iso': str(data['currency']).upper()},
        'callback_url': data['callback_url'],
    }

    customer = data.get('customer') or {}
    if isinstance(customer, dict) and customer:
        customer_payload: dict[str, Any] = {}
        firstname = customer.get('firstname') or ''
        lastname = customer.get('lastname') or ''
        email = customer.get('email') or ''
        phone = customer.get('phone') or ''
        country = str(data.get('country', '')).upper()

        if firstname:
            customer_payload['firstname'] = firstname
        if lastname:
            customer_payload['lastname'] = lastname
        if email:
            customer_payload['email'] = email
        if phone:
            customer_payload['phone_number'] = {
                'number': phone,
                'country': country,
            }

        if customer_payload:
            payload['customer'] = customer_payload

    metadata = data.get('metadata')
    if isinstance(metadata, dict) and metadata:
        payload['custom_metadata'] = metadata

    return payload


def _extract_transaction_object(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        if 'id' in payload:
            return payload
        for value in payload.values():
            if isinstance(value, dict) and 'id' in value:
                return value
    return {}


@csrf_exempt
@require_http_methods(["POST"])
def create_transaction(request):
    """Crée une transaction FedaPay via l'API REST (sans bridge PHP)."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Données JSON invalides'}, status=400)

    required_fields = ['amount', 'description', 'currency', 'country', 'callback_url']
    for field in required_fields:
        if not data.get(field):
            return JsonResponse({'success': False, 'error': f'Champ requis manquant: {field}'}, status=400)

    api_key = settings.FEDAPAY_CONFIG.get('api_key', '')
    environment = settings.FEDAPAY_CONFIG.get('environment', 'live')
    timeout_seconds = int(getattr(settings, 'FEDAPAY_API_TIMEOUT', 30))

    if not api_key:
        logger.error('Missing FEDAPAY API key in settings')
        return JsonResponse({'success': False, 'error': 'Configuration FedaPay manquante'}, status=500)

    try:
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
        base_url = _fedapay_base_url(environment)
        transaction_payload = _build_transaction_payload(data)

        create_resp = requests.post(
            f'{base_url}/transactions',
            json=transaction_payload,
            headers=headers,
            timeout=timeout_seconds,
        )
        if create_resp.status_code not in (200, 201):
            error_message = _extract_error_message(create_resp)
            logger.error(
                'FedaPay transaction create failed status=%s body=%s',
                create_resp.status_code,
                create_resp.text[:1200],
            )
            return JsonResponse({'success': False, 'error': error_message}, status=500)

        create_data = create_resp.json()
        transaction_data = _extract_transaction_object(create_data)
        transaction_id = transaction_data.get('id')
        if not transaction_id:
            logger.error('FedaPay create response without id: %s', create_data)
            return JsonResponse({'success': False, 'error': 'Réponse FedaPay invalide: transaction sans ID'}, status=500)

        token = transaction_data.get('payment_token')
        checkout_url = transaction_data.get('payment_url')

        if not token or not checkout_url:
            token_resp = requests.post(
                f'{base_url}/transactions/{transaction_id}/token',
                headers=headers,
                timeout=timeout_seconds,
            )
            if token_resp.status_code not in (200, 201):
                error_message = _extract_error_message(token_resp)
                logger.error(
                    'FedaPay token create failed tx=%s status=%s body=%s',
                    transaction_id,
                    token_resp.status_code,
                    token_resp.text[:1200],
                )
                return JsonResponse({'success': False, 'error': error_message}, status=500)

            token_data = token_resp.json()
            token = token_data.get('token')
            checkout_url = token_data.get('url')

        if not token or not checkout_url:
            logger.error('FedaPay token response invalid tx=%s body=%s', transaction_id, create_data)
            return JsonResponse({'success': False, 'error': 'Réponse FedaPay invalide: token manquant'}, status=500)

        amount_value = transaction_data.get('amount', transaction_payload['amount'])
        try:
            amount_value = int(amount_value)
        except (ValueError, TypeError):
            amount_value = int(transaction_payload['amount'])

        return JsonResponse({
            'success': True,
            'transaction_id': transaction_id,
            'token': token,
            'checkout_url': checkout_url,
            'amount': amount_value,
            'currency': str(data['currency']).upper(),
        })

    except requests.Timeout:
        logger.error('FedaPay API timeout env=%s', environment)
        return JsonResponse({'success': False, 'error': 'Timeout lors de la création de la transaction'}, status=500)
    except requests.RequestException:
        logger.exception('FedaPay API network error')
        return JsonResponse({'success': False, 'error': 'Erreur réseau lors de la création de la transaction'}, status=500)
    except Exception:
        logger.exception('Unexpected error while creating FedaPay transaction')
        return JsonResponse({'success': False, 'error': 'Erreur interne lors de la création de la transaction'}, status=500)
