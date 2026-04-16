import pytest

from bodepontoio.setup import install_bodepontoio


@pytest.fixture
def base_settings():
    return {
        "INSTALLED_APPS": ["django.contrib.auth", "django.contrib.contenttypes"],
        "REST_FRAMEWORK": {
            "DEFAULT_AUTHENTICATION_CLASSES": [
                "rest_framework_simplejwt.authentication.JWTAuthentication"
            ]
        },
    }


class TestInstallBodePontoIo:
    def test_adds_required_apps(self, base_settings):
        install_bodepontoio(base_settings)
        for app in ["bodepontoio", "rest_framework", "rest_framework_simplejwt", "rest_framework_simplejwt.token_blacklist"]:
            assert app in base_settings["INSTALLED_APPS"]

    def test_preserves_existing_apps(self, base_settings):
        install_bodepontoio(base_settings)
        assert "django.contrib.auth" in base_settings["INSTALLED_APPS"]

    def test_does_not_duplicate_apps(self, base_settings):
        base_settings["INSTALLED_APPS"].append("bodepontoio")
        install_bodepontoio(base_settings)
        assert base_settings["INSTALLED_APPS"].count("bodepontoio") == 1

    def test_prepends_email_or_username_backend(self, base_settings):
        install_bodepontoio(base_settings)
        backends = base_settings["AUTHENTICATION_BACKENDS"]
        assert backends[0] == "bodepontoio.backends.EmailOrUsernameBackend"

    def test_preserves_existing_backends(self, base_settings):
        base_settings["AUTHENTICATION_BACKENDS"] = ["myapp.backends.CustomBackend"]
        install_bodepontoio(base_settings)
        assert "myapp.backends.CustomBackend" in base_settings["AUTHENTICATION_BACKENDS"]

    def test_does_not_duplicate_backend(self, base_settings):
        base_settings["AUTHENTICATION_BACKENDS"] = ["bodepontoio.backends.EmailOrUsernameBackend"]
        install_bodepontoio(base_settings)
        backends = base_settings["AUTHENTICATION_BACKENDS"]
        assert backends.count("bodepontoio.backends.EmailOrUsernameBackend") == 1

    def test_sets_exception_handler(self, base_settings):
        install_bodepontoio(base_settings)
        assert base_settings["REST_FRAMEWORK"]["EXCEPTION_HANDLER"] == "bodepontoio.exceptions.exception_handler"

    def test_sets_renderer(self, base_settings):
        install_bodepontoio(base_settings)
        assert "bodepontoio.renderers.SuccessJSONRenderer" in base_settings["REST_FRAMEWORK"]["DEFAULT_RENDERER_CLASSES"]

    def test_does_not_overwrite_existing_exception_handler(self, base_settings):
        base_settings["REST_FRAMEWORK"]["EXCEPTION_HANDLER"] = "myapp.exceptions.handler"
        install_bodepontoio(base_settings)
        assert base_settings["REST_FRAMEWORK"]["EXCEPTION_HANDLER"] == "myapp.exceptions.handler"

    def test_does_not_overwrite_existing_renderer(self, base_settings):
        base_settings["REST_FRAMEWORK"]["DEFAULT_RENDERER_CLASSES"] = ["myapp.renderers.MyRenderer"]
        install_bodepontoio(base_settings)
        assert base_settings["REST_FRAMEWORK"]["DEFAULT_RENDERER_CLASSES"] == ["myapp.renderers.MyRenderer"]

    def test_preserves_existing_rest_framework_keys(self, base_settings):
        install_bodepontoio(base_settings)
        auth_classes = base_settings["REST_FRAMEWORK"]["DEFAULT_AUTHENTICATION_CLASSES"]
        assert "rest_framework_simplejwt.authentication.JWTAuthentication" in auth_classes

    def test_sets_bodepontoio_options(self, base_settings):
        install_bodepontoio(base_settings, FRONTEND_URL="https://myapp.com", GOOGLE_CLIENT_ID="abc")
        assert base_settings["BODEPONTOIO"] == {"FRONTEND_URL": "https://myapp.com", "GOOGLE_CLIENT_ID": "abc"}

    def test_empty_options(self, base_settings):
        install_bodepontoio(base_settings)
        assert base_settings["BODEPONTOIO"] == {}

    def test_works_on_empty_settings(self):
        settings = {}
        install_bodepontoio(settings)
        assert "bodepontoio" in settings["INSTALLED_APPS"]
        assert "AUTHENTICATION_BACKENDS" in settings
        assert "REST_FRAMEWORK" in settings
