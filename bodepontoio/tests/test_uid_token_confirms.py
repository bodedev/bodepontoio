"""The three uid+token confirm endpoints share one decode-and-fetch block.

With an integer primary key a malformed uid raises ValueError, which the except
tuple catches, so the client gets the intended "inválido ou expirado" message.
With a UUID primary key it raises ``django.core.exceptions.ValidationError``,
which was not in the tuple. DRF's ``run_validation`` catches that one itself and
still answers 400, so nothing crashed -- but the message reaching the client was
Django's internal text, ``"x" is not a valid UUID.``, instead of ours.

The test user model here has an integer pk, so the UUID path is simulated by
making the manager raise what a UUIDField would.
"""

import base64

import pytest
from django.core.exceptions import ValidationError as DjangoValidationError

from bodepontoio import serializers as serializers_module

# Well-formed base64, so decode_uid succeeds and the failure lands on the
# primary-key lookup -- which is the only place a UUIDField gets to complain.
BAD_UID = base64.urlsafe_b64encode(b"nao-e-um-uuid").decode()
DJANGO_INTERNAL_MESSAGE = "is not a valid UUID"

POST_CONFIRMS = [
    ("/auth/login/magic/confirm/", {"LOGIN_STRATEGY": "magic_link"}, "Link inválido ou expirado."),
    ("/auth/password/reset/confirm/", {}, "UID inválido."),
]


@pytest.fixture
def uuid_pk_rejects_uid(monkeypatch):
    """Make the user lookup fail the way a UUID primary key fails."""

    class _Manager:
        def get(self, *args, **kwargs):
            raise DjangoValidationError(f"“{BAD_UID}” {DJANGO_INTERNAL_MESSAGE}.")

    monkeypatch.setattr(serializers_module.User, "objects", _Manager())


def _messages(response):
    return [error["message"] for error in response.data["errors"]]


@pytest.mark.django_db
@pytest.mark.parametrize("path,bodepontoio_settings,expected", POST_CONFIRMS)
def test_malformed_uid_reports_our_message(
    api_client, uuid_pk_rejects_uid, path, bodepontoio_settings, expected, settings
):
    settings.BODEPONTOIO = bodepontoio_settings
    response = api_client.post(
        path,
        {"uid": BAD_UID, "token": "irrelevante", "new_password": "uma-senha-nova"},
    )
    assert response.status_code == 400
    assert _messages(response) == [expected]


@pytest.mark.django_db
def test_malformed_uid_in_email_confirm_reports_our_message(api_client, uuid_pk_rejects_uid):
    """This one takes uid and token from the URL, not the body."""
    response = api_client.get(f"/auth/email/confirm/{BAD_UID}/irrelevante/")
    assert response.status_code == 400
    assert _messages(response) == ["Link de confirmação inválido ou expirado."]
