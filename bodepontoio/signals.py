from django.contrib.auth.signals import user_logged_in

from bodepontoio.utils.cleaners import get_client_ip


def save_login_record(sender, user, request, **kwargs):
    from bodepontoio.models import LoginRecord

    LoginRecord.objects.create(user=user, ip=get_client_ip(request))


user_logged_in.connect(save_login_record)
