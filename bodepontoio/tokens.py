import base64

from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator, default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import base36_to_int

from .conf import bodepontoio_settings


def make_uid(user):
    return base64.urlsafe_b64encode(force_bytes(user.pk)).decode()


def decode_uid(uid_b64):
    return force_str(base64.urlsafe_b64decode(uid_b64))


def make_reset_token(user):
    return default_token_generator.make_token(user)


def check_reset_token(user, token):
    return default_token_generator.check_token(user, token)


def login_token_reuse_window() -> int:
    """Seconds a login link stays reusable, or 0 for single-use. Capped by
    PASSWORD_RESET_TIMEOUT, which ``check_token`` applies before ours.

    A negative setting clamps to 0 (single-use). Left as-is it would read as
    "window on" everywhere while ``check_token`` compared an elapsed time
    against a negative bound, so every link would fail with no error to explain
    it."""
    window = bodepontoio_settings.LOGIN_MAGIC_LINK_REUSE_WINDOW_SECONDS or 0
    return max(0, min(window, settings.PASSWORD_RESET_TIMEOUT))


def login_token_ttl_seconds() -> int:
    """Effective validity of a login link, in seconds."""
    return login_token_reuse_window() or settings.PASSWORD_RESET_TIMEOUT


class LoginTokenGenerator(PasswordResetTokenGenerator):
    """Login magic link, single-use by default.

    With ``LOGIN_MAGIC_LINK_REUSE_WINDOW_SECONDS`` set, ``last_login`` drops out
    of the hash and the link stays reusable for that long. Single-use means
    whatever opens the URL first burns the user's access (provider link
    scanners, mail-app webviews, prerender), and it kills every other pending
    link for them too, so re-sending does not help. It also protects less than
    it looks like: whoever reaches the inbox can just request another link. The
    window trades that for a deadline, which is why it should be short.

    Password and email changes invalidate pending links in either mode.
    """

    key_salt = "bodepontoio.tokens.LoginTokenGenerator"

    def _make_hash_value(self, user, timestamp):
        if not login_token_reuse_window():
            # Django's hash, with last_login: redeeming burns the link.
            return super()._make_hash_value(user, timestamp)
        email = getattr(user, user.get_email_field_name(), "") or ""
        return f"{user.pk}{user.password}{timestamp}{email}"

    def check_token(self, user, token):
        # super() validates the HMAC and the PASSWORD_RESET_TIMEOUT ceiling.
        if not super().check_token(user, token):
            return False
        window = login_token_reuse_window()
        if not window:
            return True
        ts = base36_to_int(token.split("-")[0])
        return (self._num_seconds(self._now()) - ts) <= window


login_token_generator = LoginTokenGenerator()


def make_login_token(user):
    return login_token_generator.make_token(user)


def check_login_token(user, token):
    return login_token_generator.check_token(user, token)


class EmailConfirmationTokenGenerator(PasswordResetTokenGenerator):
    key_salt = "bodepontoio.tokens.EmailConfirmationTokenGenerator"

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{timestamp}{user.auth.is_email_verified}"


email_confirmation_token_generator = EmailConfirmationTokenGenerator()


def make_confirmation_token(user):
    return email_confirmation_token_generator.make_token(user)


def check_confirmation_token(user, token):
    return email_confirmation_token_generator.check_token(user, token)
