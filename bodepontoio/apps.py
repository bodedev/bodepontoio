import warnings

from django.apps import AppConfig
from django.conf import settings


class BodePontoIoConfig(AppConfig):
    name = "bodepontoio"
    label = "bodepontoio"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        import bodepontoio.conf  # noqa: F401 — eagerly catches misconfiguration at startup

        installed_apps = settings.INSTALLED_APPS

        required = [
            ("rest_framework", "djangorestframework"),
            ("rest_framework_simplejwt", "djangorestframework-simplejwt"),
            ("rest_framework_simplejwt.token_blacklist", "djangorestframework-simplejwt (token_blacklist)"),
        ]
        for app, pkg in required:
            if app not in installed_apps:
                warnings.warn(
                    f"bodepontoio requires '{app}' in INSTALLED_APPS. "
                    f"Install it with: pip install {pkg}",
                    stacklevel=2,
                )

        if getattr(settings, "AUTH_USER_MODEL", None) != "bodepontoio.User":
            warnings.warn(
                "bodepontoio requires AUTH_USER_MODEL = \"bodepontoio.User\" in settings.",
                stacklevel=2,
            )