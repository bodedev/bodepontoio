from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

MX_CHECK_ENABLED = {"PASSWORDLESS_LOGIN_MX_CHECK_ENABLED": True}


@pytest.fixture(autouse=True)
def clear_mx_cache():
    cache.clear()
    yield
    cache.clear()


class TestDomainHasMxRecordCaching:
    @patch("bodepontoio.serializers.domain_has_mx_record")
    def test_result_is_cached(self, mock_domain_has_mx_record):
        from bodepontoio.serializers import _domain_has_mx_record

        mock_domain_has_mx_record.return_value = True
        assert _domain_has_mx_record("cached.com") is True
        assert _domain_has_mx_record("cached.com") is True
        mock_domain_has_mx_record.assert_called_once()

    @patch("bodepontoio.serializers.domain_has_mx_record")
    def test_transient_failure_fails_open_and_is_not_cached(self, mock_domain_has_mx_record):
        from bodepontoio.serializers import _domain_has_mx_record

        mock_domain_has_mx_record.return_value = None
        assert _domain_has_mx_record("retry-me.com") is True
        assert _domain_has_mx_record("retry-me.com") is True
        assert mock_domain_has_mx_record.call_count == 2

    @patch("bodepontoio.serializers.domain_has_mx_record")
    def test_no_mx_record_returns_false(self, mock_domain_has_mx_record):
        from bodepontoio.serializers import _domain_has_mx_record

        mock_domain_has_mx_record.return_value = False
        assert _domain_has_mx_record("gamail.comm") is False


@pytest.mark.django_db
class TestPasswordlessLoginMxValidation:
    OTP_STRATEGY = {"LOGIN_STRATEGY": "otp", **MX_CHECK_ENABLED}

    @override_settings(BODEPONTOIO={"LOGIN_STRATEGY": "otp"})
    def test_disabled_by_default_no_dns_lookup(self, api_client, create_user):
        create_user(email="user@example.com")
        with patch("bodepontoio.serializers.domain_has_mx_record") as mock_domain_has_mx_record:
            response = api_client.post("/auth/login/", {"email": "user@example.com"})
        assert response.status_code == 200
        mock_domain_has_mx_record.assert_not_called()

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    @patch("bodepontoio.serializers.domain_has_mx_record")
    def test_enabled_rejects_domain_without_mx(self, mock_domain_has_mx_record):
        mock_domain_has_mx_record.return_value = False
        response = APIClient().post("/auth/login/", {"email": "user@gamail.comm"})
        assert response.status_code == 400

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    @patch("bodepontoio.serializers.domain_has_mx_record")
    def test_enabled_accepts_domain_with_mx(self, mock_domain_has_mx_record, create_user):
        create_user(email="user@example.com")
        mock_domain_has_mx_record.return_value = True
        response = APIClient().post("/auth/login/", {"email": "user@example.com"})
        assert response.status_code == 200

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    @patch("bodepontoio.serializers.domain_has_mx_record")
    def test_enabled_fails_open_on_transient_dns_failure(self, mock_domain_has_mx_record, create_user):
        create_user(email="user@example.com")
        mock_domain_has_mx_record.return_value = None
        response = APIClient().post("/auth/login/", {"email": "user@example.com"})
        assert response.status_code == 200


@pytest.mark.django_db
class TestRegisterMxValidation:
    def test_disabled_by_default_no_dns_lookup(self, api_client):
        with patch("bodepontoio.serializers.domain_has_mx_record") as mock_domain_has_mx_record:
            response = api_client.post(
                "/auth/register/",
                {"email": "new@example.com", "password": "testpassword123"},
            )
        assert response.status_code == 201
        mock_domain_has_mx_record.assert_not_called()

    @override_settings(BODEPONTOIO=MX_CHECK_ENABLED)
    @patch("bodepontoio.serializers.domain_has_mx_record")
    def test_enabled_rejects_domain_without_mx(self, mock_domain_has_mx_record, api_client):
        mock_domain_has_mx_record.return_value = False
        response = api_client.post(
            "/auth/register/",
            {"email": "new@gamail.comm", "password": "testpassword123"},
        )
        assert response.status_code == 400

    @override_settings(BODEPONTOIO=MX_CHECK_ENABLED)
    @patch("bodepontoio.serializers.domain_has_mx_record")
    def test_enabled_accepts_domain_with_mx(self, mock_domain_has_mx_record, api_client):
        mock_domain_has_mx_record.return_value = True
        response = api_client.post(
            "/auth/register/",
            {"email": "new@example.com", "password": "testpassword123"},
        )
        assert response.status_code == 201
