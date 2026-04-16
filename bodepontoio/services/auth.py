from django.contrib.auth import authenticate, get_user_model
from rest_framework.exceptions import AuthenticationFailed

from ..models import OTPCode
from ..otp import verify_otp

User = get_user_model()


def _get_user_by_email(email: str):
    try:
        return User.objects.get(email=email)
    except User.DoesNotExist:
        raise AuthenticationFailed("Código inválido ou expirado.") from None


def _verify_otp(user, code: str, purpose) -> None:
    success, error = verify_otp(user, code, purpose)
    if not success:
        raise AuthenticationFailed(error)


def login_with_password(request, login: str, password: str):
    user = authenticate(request=request, username=login, password=password)

    if not user:
        raise AuthenticationFailed("Credenciais inválidas.")
    if not user.is_active:
        raise AuthenticationFailed("Conta de usuário desativada.")
    if not user.auth.is_email_verified:
        raise AuthenticationFailed("Endereço de e-mail não confirmado.")

    return user


def login_with_otp(email: str, code: str):
    user = _get_user_by_email(email)

    if not user.is_active:
        raise AuthenticationFailed("Conta de usuário desativada.")

    _verify_otp(user, code, OTPCode.Purpose.LOGIN)

    if not user.auth.is_email_verified:
        user.auth.is_email_verified = True
        user.auth.save(update_fields=["is_email_verified"])

    return user


def confirm_email_with_otp(email: str, code: str) -> None:
    user = _get_user_by_email(email)
    _verify_otp(user, code, OTPCode.Purpose.EMAIL_CONFIRM)
    user.auth.is_email_verified = True
    user.auth.save(update_fields=["is_email_verified"])


def verify_password_reset_otp(email: str, code: str):
    user = _get_user_by_email(email)
    _verify_otp(user, code, OTPCode.Purpose.PASSWORD_RESET)
    return user
