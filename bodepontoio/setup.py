_REQUIRED_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "bodepontoio",
]


def install_bodepontoio(settings: dict, **options) -> None:
    """
    Wire bodepontoio into a Django project from settings.py.

    Usage::

        # settings.py
        from bodepontoio import install_bodepontoio

        # ... your settings ...

        install_bodepontoio(
            globals(),
            FRONTEND_URL="https://myapp.com",
            GOOGLE_CLIENT_ID="your-client-id",
        )

    ``options`` maps directly to the ``BODEPONTOIO`` settings dict.
    All keys are optional — see bodepontoio.conf.DEFAULTS for the full list.
    """
    _patch_installed_apps(settings)
    _patch_authentication_backends(settings)
    _patch_rest_framework(settings)
    settings["BODEPONTOIO"] = options


def _patch_installed_apps(settings: dict) -> None:
    installed = list(settings.get("INSTALLED_APPS", []))
    for app in _REQUIRED_APPS:
        if app not in installed:
            installed.append(app)
    settings["INSTALLED_APPS"] = installed


def _patch_authentication_backends(settings: dict) -> None:
    default = ["django.contrib.auth.backends.ModelBackend"]
    backends = list(settings.get("AUTHENTICATION_BACKENDS", default))
    backend = "bodepontoio.backends.EmailOrUsernameBackend"
    if backend not in backends:
        backends.insert(0, backend)
    settings["AUTHENTICATION_BACKENDS"] = backends


def _patch_rest_framework(settings: dict) -> None:
    rf = dict(settings.get("REST_FRAMEWORK", {}))
    rf.setdefault("EXCEPTION_HANDLER", "bodepontoio.exceptions.exception_handler")
    rf.setdefault(
        "DEFAULT_RENDERER_CLASSES",
        ["bodepontoio.renderers.SuccessJSONRenderer"],
    )
    settings["REST_FRAMEWORK"] = rf
