from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .conf import bodepontoio_settings
from .models import OTPCode
from .otp import generate_otp
from .tokens import make_confirmation_token, make_reset_token, make_uid


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

    context = {
        "user": user,
        "reset_url": reset_url,
        "brand_color": bodepontoio_settings.EMAIL_BRAND_COLOR,
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
    expiry_minutes = bodepontoio_settings.OTP_EXPIRY_SECONDS // 60

    context = {
        "user": user,
        "otp_code": otp.code,
        "expiry_minutes": expiry_minutes,
        "brand_color": bodepontoio_settings.EMAIL_BRAND_COLOR,
    }
    html_message = render_to_string("bodepontoio/password_reset_otp.html", context)

    send_mail(
        subject="Redefina sua senha",
        message=f"Use o código abaixo para redefinir sua senha:\n\n{otp.code}\n\nEste código expira em {expiry_minutes} minutos.",
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

    context = {
        "user": user,
        "confirm_url": confirm_url,
        "brand_color": bodepontoio_settings.EMAIL_BRAND_COLOR,
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


def send_login_otp_email(user):
    otp = generate_otp(user, OTPCode.Purpose.LOGIN)
    expiry_minutes = bodepontoio_settings.OTP_EXPIRY_SECONDS // 60

    context = {
        "user": user,
        "otp_code": otp.code,
        "expiry_minutes": expiry_minutes,
        "brand_color": bodepontoio_settings.EMAIL_BRAND_COLOR,
    }
    html_message = render_to_string("bodepontoio/login_otp.html", context)

    send_mail(
        subject="Seu código de acesso",
        message=f"Use o código abaixo para acessar sua conta:\n\n{otp.code}\n\nEste código expira em {expiry_minutes} minutos.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )


def _send_email_confirmation_otp(user):
    otp = generate_otp(user, OTPCode.Purpose.EMAIL_CONFIRM)
    expiry_minutes = bodepontoio_settings.OTP_EXPIRY_SECONDS // 60

    context = {
        "user": user,
        "otp_code": otp.code,
        "expiry_minutes": expiry_minutes,
        "brand_color": bodepontoio_settings.EMAIL_BRAND_COLOR,
    }
    html_message = render_to_string("bodepontoio/email_confirmation_otp.html", context)

    send_mail(
        subject="Confirme seu endereço de e-mail",
        message=f"Use o código abaixo para confirmar seu endereço de e-mail:\n\n{otp.code}\n\nEste código expira em {expiry_minutes} minutos.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )
