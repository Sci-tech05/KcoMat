import logging
from typing import Any
from urllib.parse import urlparse

import requests
from django.conf import settings


logger = logging.getLogger(__name__)


def _fedapay_base_url(environment: str) -> str:
    env = (environment or "").strip().lower()
    if env == "sandbox":
        return "https://sandbox-api.fedapay.com/v1"
    return "https://api.fedapay.com/v1"


def _extract_error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = {}

    if isinstance(payload, dict):
        for key in ("message", "error", "detail"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return f"Erreur HTTP FedaPay ({response.status_code})"


def _build_transaction_payload(data: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "amount": int(data["amount"]),
        "description": data["description"],
        "currency": {"iso": str(data["currency"]).upper()},
        "callback_url": data["callback_url"],
    }

    customer = data.get("customer") or {}
    if isinstance(customer, dict) and customer:
        customer_payload: dict[str, Any] = {}
        firstname = customer.get("firstname") or ""
        lastname = customer.get("lastname") or ""
        email = customer.get("email") or ""
        phone = customer.get("phone") or ""
        country = str(data.get("country", "")).upper()

        if firstname:
            customer_payload["firstname"] = firstname
        if lastname:
            customer_payload["lastname"] = lastname
        if email:
            customer_payload["email"] = email
        if phone:
            customer_payload["phone_number"] = {
                "number": phone,
                "country": country,
            }

        if customer_payload:
            payload["customer"] = customer_payload

    metadata = data.get("metadata")
    if isinstance(metadata, dict) and metadata:
        payload["custom_metadata"] = metadata

    return payload


def _extract_transaction_object(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        if "id" in payload:
            return payload
        for value in payload.values():
            if isinstance(value, dict) and "id" in value:
                return value
    return {}


def create_fedapay_transaction(data: dict[str, Any]) -> dict[str, Any]:
    api_key = settings.FEDAPAY_CONFIG.get("api_key", "")
    environment = settings.FEDAPAY_CONFIG.get("environment", "live")
    timeout_seconds = int(getattr(settings, "FEDAPAY_API_TIMEOUT", 30))

    if not api_key:
        logger.error("Missing FEDAPAY API key in settings")
        return {"success": False, "error": "Configuration FedaPay manquante", "status_code": 500}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    base_url = _fedapay_base_url(environment)

    try:
        transaction_payload = _build_transaction_payload(data)
        create_resp = requests.post(
            f"{base_url}/transactions",
            json=transaction_payload,
            headers=headers,
            timeout=timeout_seconds,
        )
        if create_resp.status_code not in (200, 201):
            error_message = _extract_error_message(create_resp)
            logger.error(
                "FedaPay transaction create failed status=%s body=%s",
                create_resp.status_code,
                create_resp.text[:1200],
            )
            return {"success": False, "error": error_message, "status_code": 500}

        create_data = create_resp.json()
        transaction_data = _extract_transaction_object(create_data)
        transaction_id = transaction_data.get("id")
        if not transaction_id:
            logger.error("FedaPay create response without id: %s", create_data)
            return {"success": False, "error": "Réponse FedaPay invalide: transaction sans ID", "status_code": 500}

        token = transaction_data.get("payment_token")
        checkout_url = transaction_data.get("payment_url")

        if not token or not checkout_url:
            token_resp = requests.post(
                f"{base_url}/transactions/{transaction_id}/token",
                headers=headers,
                timeout=timeout_seconds,
            )
            if token_resp.status_code not in (200, 201):
                error_message = _extract_error_message(token_resp)
                logger.error(
                    "FedaPay token create failed tx=%s status=%s body=%s",
                    transaction_id,
                    token_resp.status_code,
                    token_resp.text[:1200],
                )
                return {"success": False, "error": error_message, "status_code": 500}

            token_data = token_resp.json()
            token = token_data.get("token")
            checkout_url = token_data.get("url")

        if not token or not checkout_url:
            logger.error("FedaPay token response invalid tx=%s body=%s", transaction_id, create_data)
            return {"success": False, "error": "Réponse FedaPay invalide: token manquant", "status_code": 500}

        amount_value = transaction_data.get("amount", transaction_payload["amount"])
        try:
            amount_value = int(amount_value)
        except (ValueError, TypeError):
            amount_value = int(transaction_payload["amount"])

        return {
            "success": True,
            "transaction_id": transaction_id,
            "token": token,
            "checkout_url": checkout_url,
            "amount": amount_value,
            "currency": str(data["currency"]).upper(),
            "status_code": 200,
        }
    except requests.Timeout:
        logger.error("FedaPay API timeout env=%s", environment)
        return {"success": False, "error": "Timeout lors de la création de la transaction", "status_code": 500}
    except requests.RequestException as exc:
        logger.exception("FedaPay API network error")
        host = urlparse(base_url).netloc or "api.fedapay.com"
        details = str(exc).strip()
        error_message = f"Erreur réseau lors de la création de la transaction ({host})"
        if details:
            error_message = f"{error_message}: {details}"
        error_message = (
            f"{error_message}. "
            "Sur PythonAnywhere, vérifiez que la sortie HTTPS vers ce domaine est autorisée."
        )
        return {"success": False, "error": error_message, "status_code": 500}
    except Exception:
        logger.exception("Unexpected error while creating FedaPay transaction")
        return {"success": False, "error": "Erreur interne lors de la création de la transaction", "status_code": 500}


def fetch_fedapay_transaction(transaction_id) -> dict[str, Any]:
    """Lit une transaction FedaPay par son id (cote serveur, cle secrete)."""
    transaction_id = str(transaction_id or "").strip()
    if not transaction_id.isdigit():
        return {}

    api_key = settings.FEDAPAY_CONFIG.get("api_key", "")
    environment = settings.FEDAPAY_CONFIG.get("environment", "live")
    timeout_seconds = int(getattr(settings, "FEDAPAY_API_TIMEOUT", 30))
    if not api_key:
        logger.error("Missing FEDAPAY API key while fetching transaction")
        return {}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.get(
            f"{_fedapay_base_url(environment)}/transactions/{transaction_id}",
            headers=headers,
            timeout=timeout_seconds,
        )
    except requests.RequestException:
        logger.exception("Network error while fetching FedaPay transaction %s", transaction_id)
        return {}

    if response.status_code != 200:
        logger.warning(
            "FedaPay transaction fetch failed id=%s status=%s body=%s",
            transaction_id,
            response.status_code,
            response.text[:1200],
        )
        return {}

    try:
        return _extract_transaction_object(response.json())
    except ValueError:
        logger.warning("FedaPay transaction fetch returned non-JSON body id=%s", transaction_id)
        return {}


def _metadata_matches(transaction: dict[str, Any], expected_type: str, ref_key: str, expected_ref) -> bool | None:
    """True/False si les metadonnees sont presentes, None si FedaPay ne les renvoie pas."""
    metadata = transaction.get("custom_metadata") or transaction.get("metadata")
    if not isinstance(metadata, dict) or not metadata:
        return None
    return (
        str(metadata.get("type", "")) == expected_type
        and str(metadata.get(ref_key, "")) == str(expected_ref)
    )


def verify_fedapay_payment(
    *,
    stored_transaction_id,
    candidate_transaction_id=None,
    expected_amount,
    expected_type: str,
    ref_key: str,
    expected_ref,
) -> str | None:
    """
    Verifie qu'un paiement FedaPay correspond exactement a l'objet attendu.

    - La transaction stockee en base (creee par le serveur pour cet objet) est la
      reference ; elle doit etre approuvee, du bon montant et de la bonne devise.
    - Un id fourni par l'URL/le webhook (candidate) n'est accepte que si FedaPay
      confirme en plus des metadonnees pointant vers CE type et CETTE reference
      (cas ou l'utilisateur a relance le paiement et ecrase l'id stocke).

    Retourne l'id de la transaction validee, ou None.
    """
    stored_id = str(stored_transaction_id or "").strip()
    candidate_id = str(candidate_transaction_id or "").strip()

    checks = []
    if stored_id:
        checks.append((stored_id, False))
    if candidate_id and candidate_id != stored_id:
        checks.append((candidate_id, True))

    expected_currency = str(settings.PAYMENT_CONFIG.get("currency", "XOF")).upper()

    for transaction_id, metadata_required in checks:
        transaction = fetch_fedapay_transaction(transaction_id)
        if not transaction:
            continue
        if str(transaction.get("id", "")) != transaction_id:
            continue
        if str(transaction.get("status", "")).strip().lower() != "approved":
            continue

        try:
            amount = int(transaction.get("amount"))
        except (TypeError, ValueError):
            amount = None
        if amount != int(expected_amount):
            logger.warning(
                "FedaPay amount mismatch tx=%s type=%s ref=%s got=%s expected=%s",
                transaction_id, expected_type, expected_ref, amount, expected_amount,
            )
            continue

        currency = transaction.get("currency")
        currency_iso = currency.get("iso") if isinstance(currency, dict) else currency
        if currency_iso and str(currency_iso).upper() != expected_currency:
            logger.warning("FedaPay currency mismatch tx=%s got=%s", transaction_id, currency_iso)
            continue

        metadata_ok = _metadata_matches(transaction, expected_type, ref_key, expected_ref)
        if metadata_ok is False or (metadata_required and metadata_ok is not True):
            logger.warning(
                "FedaPay metadata mismatch tx=%s type=%s ref=%s",
                transaction_id, expected_type, expected_ref,
            )
            continue

        return transaction_id

    return None
