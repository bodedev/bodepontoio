from math import ceil
from urllib.parse import quote

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .conf import bodepontoio_settings
from .models import OTPCode
from .otp import generate_otp
from .tokens import (
    login_token_ttl_seconds,
    make_confirmation_token,
    make_login_token,
    make_reset_token,
    make_uid,
)


def _expiry(seconds):
    """Human-readable validity for an email: template context plus a phrase for
    the plain-text body.

    Anything under two hours reads better in minutes. Always rounds up, because
    an email must never promise less time than the link or code actually has --
    that sends people back for a new one while the old one still works. The
    phrase is the single source of truth for the wording, so the templates do
    not each re-derive it and drift. ``expiry_hours``/``expiry_minutes`` are kept
    in the context for projects whose overridden templates already read them.
    """
    if seconds < 2 * 3600:
        minutes = max(1, ceil(seconds / 60))
        return {
            "expiry_hours": 0,
            "expiry_minutes": minutes,
            "expiry_phrase": f"{minutes} minuto{'' if minutes == 1 else 's'}",
        }
    hours = ceil(seconds / 3600)
    return {
        "expiry_hours": hours,
        "expiry_minutes": 0,
        "expiry_phrase": f"{hours} hora{'' if hours == 1 else 's'}",
    }


def send_password_reset_email(user):
    if bodepontoio_settings.PASSWORD_RESET_STRATEGY == "otp":
        _send_password_reset_otp(user)
    else:
        _send_password_reset_magic_link(user)


def send_email_confirmation_email(user, request):
    if bodepontoio_settings.EMAIL_CONFIRM_STRATEGY == "otp":
        _send_email_confirmation_otp(user)
    else:
        _send_email_confirmation_magic_link(user, request)


def _send_password_reset_magic_link(user):
    uid = make_uid(user)
    token = make_reset_token(user)

    reset_url = (
        bodepontoio_settings.FRONTEND_URL
        + bodepontoio_settings.PASSWORD_RESET_URL_PATH.format(uid=uid, token=token)
    )

    # The reset token is Django's, so PASSWORD_RESET_TIMEOUT is the real deadline.
    context = {
        "user": user,
        "reset_url": reset_url,
        "brand_color": bodepontoio_settings.EMAIL_BRAND_COLOR,
        **_expiry(settings.PASSWORD_RESET_TIMEOUT),
    }
    html_message = render_to_string("bodepontoio/password_reset_email.html", context)

    send_mail(
        subject="Redefina sua senha",
        message=f"Clique no link abaixo para redefinir sua senha:\n\n{reset_url}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )


def _send_password_reset_otp(user):
    otp = generate_otp(user, OTPCode.Purpose.PASSWORD_RESET)
    expiry = _expiry(bodepontoio_settings.OTP_EXPIRY_SECONDS)

    context = {
        "user": user,
        "otp_code": otp.code,
        "brand_color": bodepontoio_settings.EMAIL_BRAND_COLOR,
        **expiry,
    }
    html_message = render_to_string("bodepontoio/password_reset_otp.html", context)

    send_mail(
        subject="Redefina sua senha",
        message=f"Use o código abaixo para redefinir sua senha:\n\n{otp.code}\n\nEste código expira em {expiry['expiry_phrase']}.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )


def _send_email_confirmation_magic_link(user, request):
    uid = make_uid(user)
    token = make_confirmation_token(user)

    confirm_url = (
        bodepontoio_settings.FRONTEND_URL
        + bodepontoio_settings.EMAIL_CONFIRM_URL_PATH.format(uid=uid, token=token)
    )

    # EmailConfirmationTokenGenerator subclasses Django's, so the deadline is
    # PASSWORD_RESET_TIMEOUT here too.
    context = {
        "user": user,
        "confirm_url": confirm_url,
        "brand_color": bodepontoio_settings.EMAIL_BRAND_COLOR,
        **_expiry(settings.PASSWORD_RESET_TIMEOUT),
    }
    html_message = render_to_string("bodepontoio/email_confirmation_email.html", context)

    send_mail(
        subject="Confirme seu endereço de e-mail",
        message=f"Clique no link abaixo para confirmar seu endereço de e-mail:\n\n{confirm_url}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )


def send_login_email(user, next_path=""):
    if bodepontoio_settings.LOGIN_STRATEGY == "magic_link":
        _send_login_magic_link(user, next_path=next_path)
    else:
        send_login_otp_email(user)


def _send_login_magic_link(user, next_path=""):
    uid = make_uid(user)
    token = make_login_token(user)

    login_url = (
        bodepontoio_settings.FRONTEND_URL
        + bodepontoio_settings.LOGIN_MAGIC_LINK_URL_PATH.format(uid=uid, token=token)
    )
    if next_path:
        login_url += f"?next={quote(next_path, safe='/')}"

    # A short reuse window reads in minutes, the default 3-day ceiling in hours.
    context = {
        "user": user,
        "login_url": login_url,
        "brand_color": bodepontoio_settings.EMAIL_BRAND_COLOR,
        **_expiry(login_token_ttl_seconds()),
    }
    html_message = render_to_string("bodepontoio/login_magic_link.html", context)

    send_mail(
        subject="Seu link de acesso",
        message=f"Clique no link abaixo para acessar sua conta:\n\n{login_url}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )


def send_login_otp_email(user):
    otp = generate_otp(user, OTPCode.Purpose.LOGIN)
    expiry = _expiry(bodepontoio_settings.OTP_EXPIRY_SECONDS)

    context = {
        "user": user,
        "otp_code": otp.code,
        "brand_color": bodepontoio_settings.EMAIL_BRAND_COLOR,
        **expiry,
    }
    html_message = render_to_string("bodepontoio/login_otp.html", context)

    send_mail(
        subject="Seu código de acesso",
        message=f"Use o código abaixo para acessar sua conta:\n\n{otp.code}\n\nEste código expira em {expiry['expiry_phrase']}.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )


def _send_email_confirmation_otp(user):
    otp = generate_otp(user, OTPCode.Purpose.EMAIL_CONFIRM)
    expiry = _expiry(bodepontoio_settings.OTP_EXPIRY_SECONDS)

    context = {
        "user": user,
        "otp_code": otp.code,
        "brand_color": bodepontoio_settings.EMAIL_BRAND_COLOR,
        **expiry,
    }
    html_message = render_to_string("bodepontoio/email_confirmation_otp.html", context)

    send_mail(
        subject="Confirme seu endereço de e-mail",
        message=f"Use o código abaixo para confirmar seu endereço de e-mail:\n\n{otp.code}\n\nEste código expira em {expiry['expiry_phrase']}.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )
