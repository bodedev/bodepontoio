import pytest
from rest_framework.test import APIClient

from bodepontoio.models import User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def create_user(db):
    def _create_user(email="user@example.com", password="testpassword123", **kwargs):
        return User.objects.create_user(email=email, password=password, **kwargs)

    return _create_user


@pytest.fixture
def auth_client(create_user, api_client):
    user = create_user()
    api_client.force_authenticate(user=user)
    return api_client, user
