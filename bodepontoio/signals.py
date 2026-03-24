from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=get_user_model())
def create_user_auth(sender, instance, created, **kwargs):
    from bodepontoio.models import UserAuth

    if created:
        UserAuth.objects.get_or_create(user=instance)
