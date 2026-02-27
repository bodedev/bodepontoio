from django.conf import settings
from django.core.mail import send_mail

from .conf import bodepontoio_settings
from .tokens import make_reset_token, make_uid


def send_password_reset_email(user):
    uid = make_uid(user)
    token = make_reset_token(user)
    reset_url = (
        bodepontoio_settings.FRONTEND_URL
        + bodepontoio_settings.PASSWORD_RESET_URL_PATH.format(uid=uid, token=token)
    )
    send_mail(
        subject="Password Reset Request",
        message=f"Click the link below to reset your password:\n\n{reset_url}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
