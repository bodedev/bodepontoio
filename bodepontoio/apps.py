from django.apps import AppConfig


class BodepontoioConfig(AppConfig):
    name = 'bodepontoio'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        import bodepontoio.signals  # noqa: F401
