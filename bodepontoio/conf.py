from datetime import timedelta

from django.conf import settings
from django.test.signals import setting_changed

DEFAULTS = {
    "FRONTEND_URL": "http://localhost:3000",
    "PASSWORD_RESET_URL_PATH": "/reset-password/{uid}/{token}/",
    "PASSWORD_RESET_TIMEOUT_DAYS": 1,
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
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
