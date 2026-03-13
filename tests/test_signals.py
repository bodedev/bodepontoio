from unittest.mock import MagicMock

import pytest
from django.contrib.auth.signals import user_logged_in

from bodepontoio.models import LoginRecord, User


@pytest.mark.django_db
class TestSaveLoginRecordSignal:
    def test_login_creates_record(self, create_user):
        user = create_user()
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "127.0.0.1"}

        user_logged_in.send(sender=User, user=user, request=request)

        assert LoginRecord.objects.count() == 1
        record = LoginRecord.objects.first()
        assert record.user == user
        assert record.ip == "127.0.0.1"

    def test_login_with_forwarded_ip(self, create_user):
        user = create_user()
        request = MagicMock()
        request.META = {"HTTP_X_FORWARDED_FOR": "10.0.0.1, 192.168.1.1"}

        user_logged_in.send(sender=User, user=user, request=request)

        record = LoginRecord.objects.first()
        assert record.ip == "10.0.0.1"
