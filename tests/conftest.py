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
    def _create_user(email="user@example.com", password="testpassword123", is_email_verified=False, **kwargs):
        User = get_user_model()
        user = User.objects.create_user(username=email, email=email, password=password, **kwargs)
        user.profile.is_email_verified = is_email_verified
        user.profile.save(update_fields=["is_email_verified"])
        return user

    return _create_user


@pytest.fixture
def auth_client(create_user, api_client):
    user = create_user()
    api_client.force_authenticate(user=user)
    return api_client, user
