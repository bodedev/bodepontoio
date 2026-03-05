SECRET_KEY = "test-secret-key-for-bodepontoio-do-not-use-in-production"
DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "bodepontoio",
    "tests.testapp",
]

MIGRATION_MODULES = {"testapp": None}  # create testapp tables via syncdb, no migrations

AUTH_USER_MODEL = "bodepontoio.User"

ROOT_URLCONF = "tests.urls"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

USE_TZ = True

MIDDLEWARE = []

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [],
        },
    }
]

BODEPONTOIO = {
    "GOOGLE_CLIENT_ID": "test-client-id.apps.googleusercontent.com",
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
DEFAULT_FROM_EMAIL = "test@example.com"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "EXCEPTION_HANDLER": "bodepontoio.exceptions.exception_handler",
    "DEFAULT_RENDERER_CLASSES": ["bodepontoio.renderers.SuccessJSONRenderer"],
}
