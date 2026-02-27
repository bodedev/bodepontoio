import pytest

from bodepontoio.models import User


@pytest.mark.django_db
class TestUserManager:
    def test_create_user(self):
        user = User.objects.create_user(email="test@example.com", password="pass123")
        assert user.email == "test@example.com"
        assert user.check_password("pass123")
        assert user.is_active
        assert not user.is_staff
        assert not user.is_superuser

    def test_create_user_normalizes_email(self):
        user = User.objects.create_user(email="Test@EXAMPLE.COM", password="pass123")
        assert user.email == "Test@example.com"

    def test_create_user_requires_email(self):
        with pytest.raises(ValueError):
            User.objects.create_user(email="", password="pass123")

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            email="admin@example.com", password="admin123"
        )
        assert user.is_staff
        assert user.is_superuser

    def test_str(self):
        user = User.objects.create_user(email="str@example.com", password="pass123")
        assert str(user) == "str@example.com"

    def test_get_full_name(self):
        user = User.objects.create_user(
            email="full@example.com",
            password="pass123",
            first_name="John",
            last_name="Doe",
        )
        assert user.get_full_name() == "John Doe"

    def test_get_short_name(self):
        user = User.objects.create_user(
            email="short@example.com",
            password="pass123",
            first_name="Jane",
        )
        assert user.get_short_name() == "Jane"

    def test_username_field_is_email(self):
        assert User.USERNAME_FIELD == "email"

    def test_required_fields(self):
        assert "first_name" in User.REQUIRED_FIELDS
        assert "last_name" in User.REQUIRED_FIELDS
