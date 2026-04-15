from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver

from bodepontoio.utils.cleaners import get_client_ip


@receiver(post_save, sender=get_user_model())
def create_user_auth(sender, instance, created, **kwargs):
    from bodepontoio.models import UserAuth

    if created:
        UserAuth.objects.get_or_create(user=instance)


@receiver(user_logged_in)
def save_login_record(sender, user, request, **kwargs):
    from bodepontoio.models import LoginRecord

    client_ip = get_client_ip(request)
    LoginRecord.objects.create(
        user=user,
        ip=client_ip,
    )
