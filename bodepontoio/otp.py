import secrets
from datetime import timedelta

from django.utils import timezone

from .conf import bodepontoio_settings
from .models import OTPCode


def generate_otp(user, purpose: str) -> OTPCode:
    """
    Invalidate any existing unused OTPs for this user+purpose,
    then create and return a new one.
    """
    OTPCode.objects.filter(user=user, purpose=purpose, is_used=False).update(is_used=True)

    length = bodepontoio_settings.OTP_LENGTH
    code = "".join(str(secrets.randbelow(10)) for _ in range(length))
    expires_at = timezone.now() + timedelta(seconds=bodepontoio_settings.OTP_EXPIRY_SECONDS)

    return OTPCode.objects.create(
        user=user,
        code=code,
        purpose=purpose,
        expires_at=expires_at,
    )


def verify_otp(user, code: str, purpose: str) -> tuple[bool, str]:
    """
    Returns (success, error_message).
    Handles expiry, single-use enforcement, and max-attempts brute-force protection.
    """
    max_attempts = bodepontoio_settings.OTP_MAX_ATTEMPTS

    try:
        otp = OTPCode.objects.filter(user=user, purpose=purpose, is_used=False).latest("created")
    except OTPCode.DoesNotExist:
        return False, "Código inválido ou expirado."

    if otp.expires_at < timezone.now():
        otp.is_used = True
        otp.save(update_fields=["is_used"])
        return False, "Código expirado."

    if otp.attempts >= max_attempts:
        otp.is_used = True
        otp.save(update_fields=["is_used"])
        return False, "Número máximo de tentativas excedido. Solicite um novo código."

    if otp.code != code:
        otp.attempts += 1
        if otp.attempts >= max_attempts:
            otp.is_used = True
            otp.save(update_fields=["attempts", "is_used"])
            return False, "Número máximo de tentativas excedido. Solicite um novo código."
        otp.save(update_fields=["attempts"])
        return False, "Código inválido."

    otp.is_used = True
    otp.save(update_fields=["is_used"])
    return True, ""
