from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse

from .conf import bodepontoio_settings
from .tokens import make_confirmation_token, make_reset_token, make_uid


def send_password_reset_email(user):
    uid = make_uid(user)
    token = make_reset_token(user)

    reset_url = (
        bodepontoio_settings.FRONTEND_URL
        + bodepontoio_settings.PASSWORD_RESET_URL_PATH.format(uid=uid, token=token)
    )

    context = {
        "user": user,
        "reset_url": reset_url,
    }
    html_message = render_to_string(
        "bodepontoio/password_reset_email.html", context
    )

    send_mail(
        subject="Redefina sua senha",
        message=f"Clique no link abaixo para redefinir sua senha:\n\n{reset_url}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )


def send_email_confirmation_email(user, request):
    uid = make_uid(user)
    token = make_confirmation_token(user)

    confirm_url = request.build_absolute_uri(
        reverse("bodepontoio:email-confirm", kwargs={"uid": uid, "token": token})
    )

    context = {
        "user": user,
        "confirm_url": confirm_url,
    }
    html_message = render_to_string(
        "bodepontoio/email_confirmation_email.html", context
    )

    send_mail(
        subject="Confirme seu endereço de e-mail",
        message=f"Clique no link abaixo para confirmar seu endereço de e-mail:\n\n{confirm_url}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )
