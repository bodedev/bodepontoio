from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist


def has_username_field():
    User = get_user_model()
    try:
        User._meta.get_field("username")
    except FieldDoesNotExist:
        return False
    return True


def unique_username_for_email(email):
    User = get_user_model()
    base = email.split("@")[0]
    username = base
    suffix = 1
    while User.objects.filter(username=username).exists():
        username = f"{base}{suffix}"
        suffix += 1
    return username


def get_or_create_user_by_email(email, **extra_fields):
    from django.db import IntegrityError, transaction

    User = get_user_model()
    try:
        return User.objects.get(email=email), False
    except User.DoesNotExist:
        pass

    fields = {"email": email, **extra_fields}
    if has_username_field() and "username" not in fields:
        fields["username"] = unique_username_for_email(email)

    user = User(**fields)
    user.set_unusable_password()
    try:
        with transaction.atomic():
            user.save()
    except IntegrityError:
        return User.objects.get(email=email), False
    return user, True
