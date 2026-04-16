from django.conf import settings
from django.test.signals import setting_changed

DEFAULTS = {
    "FRONTEND_URL": "http://localhost:3000",
    "PASSWORD_RESET_URL_PATH": "/reset-password/{uid}/{token}/",
    "EMAIL_CONFIRM_URL_PATH": "/confirm-email/{uid}/{token}/",
    "GOOGLE_CLIENT_ID": None,
    "API_DEBUG_LOGGER_ENABLED": False,
    "API_DEBUG_LOGGER_PATH_PREFIX": "/api/",
    "API_DEBUG_LOGGER_MAX_BODY_CHARS": 6000,
    "EMAIL_BRAND_COLOR": "#4f46e5",
    "EMAIL_CONFIRM_STRATEGY": "magic_link",
    "PASSWORD_RESET_STRATEGY": "magic_link",
    "OTP_LENGTH": 6,
    "OTP_EXPIRY_SECONDS": 900,
    "OTP_MAX_ATTEMPTS": 5,
    "LOGIN_STRATEGY": "password",
    "USER_SERIALIZER": "bodepontoio.serializers.DefaultUserSerializer",
}


class BodePontoIoSettings:
    def __init__(self, defaults=None):
        self._defaults = defaults or DEFAULTS
        self._cached_attrs = set()

    def __getattr__(self, name):
        if name not in self._defaults:
            raise AttributeError(f"Invalid bodepontoio setting: {name!r}")
        user_settings = getattr(settings, "BODEPONTOIO", {})
        val = user_settings.get(name, self._defaults[name])
        self._cached_attrs.add(name)
        setattr(self, name, val)
        return val

    def reload(self):
        for attr in self._cached_attrs:
            self.__dict__.pop(attr, None)
        self._cached_attrs.clear()


bodepontoio_settings = BodePontoIoSettings(DEFAULTS)


def _reload_bodepontoio_settings(*args, **kwargs):
    setting = kwargs.get("setting")
    if setting == "BODEPONTOIO":
        bodepontoio_settings.reload()


setting_changed.connect(_reload_bodepontoio_settings)
