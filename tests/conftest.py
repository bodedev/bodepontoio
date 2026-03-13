import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def reset_mail_outbox():
    mail.outbox = []


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def create_user(db):
    def _create_user(email="user@example.com", password="testpassword123", **kwargs):
        User = get_user_model()
        return User.objects.create_user(username=email, email=email, password=password, **kwargs)

    return _create_user


@pytest.fixture
def auth_client(create_user, api_client):
    user = create_user()
    api_client.force_authenticate(user=user)
    return api_client, user
