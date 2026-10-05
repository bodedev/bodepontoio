import os
from typing import Any

SECRET_KEY = "test-secret-key-for-bodepontoio-do-not-use-in-production"
DEBUG = True

DATABASES: dict[str, dict[str, Any]] = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Para rodar a suíte contra MySQL (caixa/collation se comportam diferente do SQLite):
# DB_ENGINE=mysql DB_HOST=127.0.0.1 DB_PORT=13306 DB_USER=root DB_PASSWORD=ci uv run --with pymysql pytest --nomigrations
# (--nomigrations: o testapp é criado via syncdb antes das migrations e tem FK para
# auth_user; o SQLite tolera, o MySQL não.)
if os.getenv("DB_ENGINE") == "mysql":
    # PyMySQL é Python puro (o mysqlclient não tem wheel para todas as versões do
    # Python da matriz); o Django exige mysqlclient >= 2.2.1, então ajustamos a versão.
    import pymysql  # type: ignore[import-untyped]

    pymysql.version_info = (2, 2, 1, "final", 0)
    pymysql.install_as_MySQLdb()

    DATABASES["default"] = {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("DB_NAME", "bpio_ci"),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "USER": os.getenv("DB_USER", "root"),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "OPTIONS": {"charset": "utf8mb4"},
        "TEST": {"CHARSET": "utf8mb4", "COLLATION": "utf8mb4_0900_ai_ci"},
    }

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "bodepontoio",
    "bodepontoio.tests.testapp",
]

MIGRATION_MODULES = {"testapp": None}  # create testapp tables via syncdb, no migrations

ROOT_URLCONF = "bodepontoio.tests.urls"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

USE_TZ = True

MIDDLEWARE: list[str] = []

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
