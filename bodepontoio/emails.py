from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext as _

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
        subject=_("Reset your password"),
        message=_("Click the link below to reset your password:\n\n%(reset_url)s") % {"reset_url": reset_url},
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
        subject=_("Confirm your email address"),
        message=_("Click the link below to confirm your email address:\n\n%(confirm_url)s") % {"confirm_url": confirm_url},
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )
