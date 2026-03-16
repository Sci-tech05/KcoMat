import random
import time
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

SESSION_VERIFIED_USER_ID = 'admin_2fa_verified_user_id'
SESSION_CODE_HASH = 'admin_2fa_code_hash'
SESSION_CODE_EXPIRES_AT = 'admin_2fa_code_expires_at'
SESSION_ATTEMPTS = 'admin_2fa_attempts'


def _admin_prefix():
    return f"/{settings.ADMIN_URL.lstrip('/')}"


def _admin_2fa_prefix():
    return f"/{settings.ADMIN_2FA_PATH.lstrip('/')}"


def _get_client_ip(request):
    if getattr(settings, 'ADMIN_TRUST_X_FORWARDED_FOR', False):
        forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _is_ip_allowed(request):
    allowed_ips = getattr(settings, 'ADMIN_ALLOWED_IPS', []) or []
    if not allowed_ips or '*' in allowed_ips:
        return True
    return _get_client_ip(request) in allowed_ips


def _is_staff_user(user):
    return bool(user and user.is_authenticated and user.is_staff)


def _safe_next(request, next_url):
    candidate = (next_url or '').strip()
    verify_prefix = _admin_2fa_prefix()
    if candidate.startswith(verify_prefix):
        return _admin_prefix()
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return _admin_prefix()


def _clear_2fa_state(request):
    for key in (SESSION_CODE_HASH, SESSION_CODE_EXPIRES_AT, SESSION_ATTEMPTS):
        request.session.pop(key, None)


def _send_admin_2fa_code(request):
    code = f"{random.randint(0, 999999):06d}"
    ttl_seconds = max(60, int(getattr(settings, 'ADMIN_2FA_CODE_TTL_SECONDS', 300)))
    request.session[SESSION_CODE_HASH] = make_password(code)
    request.session[SESSION_CODE_EXPIRES_AT] = int(time.time()) + ttl_seconds
    request.session[SESSION_ATTEMPTS] = 0

    user_email = (request.user.email or '').strip()
    fallback_email = (getattr(settings, 'EMAIL_HOST_USER', '') or '').strip()
    recipient_email = user_email or fallback_email
    if not recipient_email:
        return None

    try:
        sent_count = send_mail(
            subject='Code de verification admin KcoMat',
            message=(
                f"Bonjour {request.user.get_username()},\n\n"
                f"Votre code de verification administrateur est: {code}\n"
                f"Ce code expire dans {ttl_seconds // 60} minute(s).\n\n"
                "Si vous n'etes pas a l'origine de cette tentative, ignorez ce message."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        if sent_count > 0:
            return recipient_email
    except Exception:
        return None
    return None


class AdminSecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        admin_prefix = _admin_prefix()
        verify_prefix = _admin_2fa_prefix()
        path = request.path

        on_admin_path = path.startswith(admin_prefix)
        on_verify_path = path.startswith(verify_prefix)

        if on_admin_path or on_verify_path:
            if not _is_ip_allowed(request):
                return HttpResponseForbidden('Acces admin refuse depuis cette adresse IP.')

            if path.startswith(f"{admin_prefix}logout/"):
                request.session.pop(SESSION_VERIFIED_USER_ID, None)
                _clear_2fa_state(request)

            # Do not redirect the 2FA verification endpoint to itself.
            if on_admin_path and not on_verify_path and _is_staff_user(request.user):
                verified_user_id = request.session.get(SESSION_VERIFIED_USER_ID)
                if verified_user_id != request.user.id:
                    query = urlencode({'next': request.get_full_path()})
                    return HttpResponseRedirect(f"{verify_prefix}?{query}")

        return self.get_response(request)


@login_required
def verify_admin_2fa(request):
    if not request.user.is_staff:
        return HttpResponseForbidden('Acces reserve aux administrateurs.')

    if not _is_ip_allowed(request):
        return HttpResponseForbidden('Acces admin refuse depuis cette adresse IP.')

    raw_next_url = request.GET.get('next') or request.POST.get('next')
    next_url = _safe_next(request, raw_next_url)
    max_attempts = max(1, int(getattr(settings, 'ADMIN_2FA_MAX_ATTEMPTS', 5)))
    expires_at = int(request.session.get(SESSION_CODE_EXPIRES_AT, 0))
    now_ts = int(time.time())

    if request.method == 'POST':
        attempts = int(request.session.get(SESSION_ATTEMPTS, 0))
        if attempts >= max_attempts:
            messages.error(request, 'Nombre maximal de tentatives atteint. Demandez un nouveau code.')
        else:
            submitted_code = (request.POST.get('code') or '').strip()
            code_hash = request.session.get(SESSION_CODE_HASH, '')
            if not code_hash or now_ts > expires_at:
                messages.error(request, 'Code expire. Un nouveau code a ete envoye.')
                _send_admin_2fa_code(request)
            elif submitted_code and check_password(submitted_code, code_hash):
                request.session[SESSION_VERIFIED_USER_ID] = request.user.id
                _clear_2fa_state(request)
                messages.success(request, 'Verification 2FA reussie.')
                return redirect(next_url)
            else:
                attempts += 1
                request.session[SESSION_ATTEMPTS] = attempts
                remaining = max_attempts - attempts
                if remaining <= 0:
                    messages.error(request, 'Trop de tentatives echouees. Demandez un nouveau code.')
                else:
                    messages.error(request, f'Code invalide. Tentatives restantes: {remaining}.')

    force_resend = request.GET.get('resend') == '1'
    if force_resend or not request.session.get(SESSION_CODE_HASH) or now_ts > expires_at:
        sent_to = _send_admin_2fa_code(request)
        if sent_to:
            messages.info(request, f'Un code de verification vient d\'etre envoye')
        else:
            messages.error(
                request,
                'Aucun email de destination n\'est configure. Renseignez l\'email du compte admin ou EMAIL_HOST_USER.'
            )

    context = {
        'next_url': next_url,
        'admin_path': _admin_prefix(),
    }
    return render(request, 'admin/admin_2fa_verify.html', context)
