import base64

from django.contrib.auth.tokens import PasswordResetTokenGenerator, default_token_generator
from django.utils.encoding import force_bytes, force_str


def make_uid(user):
    return base64.urlsafe_b64encode(force_bytes(user.pk)).decode()


def decode_uid(uid_b64):
    return force_str(base64.urlsafe_b64decode(uid_b64))


def make_reset_token(user):
    return default_token_generator.make_token(user)


def check_reset_token(user, token):
    return default_token_generator.check_token(user, token)


class EmailConfirmationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{timestamp}{user.is_email_verified}"


email_confirmation_token_generator = EmailConfirmationTokenGenerator()


def make_confirmation_token(user):
    return email_confirmation_token_generator.make_token(user)


def check_confirmation_token(user, token):
    return email_confirmation_token_generator.check_token(user, token)
