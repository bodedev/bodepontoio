import pytest

from bodepontoio.utils.passwords.generate_hash import (
    hash_password_pbkdf2,
    verify_password_pbkdf2,
)


class TestHashPasswordPbkdf2:
    def test_generates_hash_with_correct_format(self):
        result = hash_password_pbkdf2("mypassword")
        parts = result.split("$")
        assert len(parts) == 4
        assert parts[0] == "pbkdf2"
        assert parts[1] == "200000"

    def test_generates_different_hashes_for_same_password(self):
        hash1 = hash_password_pbkdf2("mypassword")
        hash2 = hash_password_pbkdf2("mypassword")
        assert hash1 != hash2

    def test_custom_iterations(self):
        result = hash_password_pbkdf2("mypassword", iterations=100000)
        parts = result.split("$")
        assert parts[1] == "100000"

    def test_raises_type_error_for_non_string(self):
        with pytest.raises(TypeError, match="password deve ser uma string"):
            hash_password_pbkdf2(12345)

    def test_raises_type_error_for_none(self):
        with pytest.raises(TypeError):
            hash_password_pbkdf2(None)

    def test_empty_password(self):
        result = hash_password_pbkdf2("")
        parts = result.split("$")
        assert len(parts) == 4
        assert parts[0] == "pbkdf2"


class TestVerifyPasswordPbkdf2:
    def test_verifies_correct_password(self):
        stored = hash_password_pbkdf2("mypassword")
        assert verify_password_pbkdf2(stored, "mypassword") is True

    def test_rejects_incorrect_password(self):
        stored = hash_password_pbkdf2("mypassword")
        assert verify_password_pbkdf2(stored, "wrongpassword") is False

    def test_rejects_invalid_format_wrong_prefix(self):
        assert verify_password_pbkdf2("invalid$200000$salt$hash", "password") is False

    def test_rejects_invalid_format_missing_parts(self):
        assert verify_password_pbkdf2("pbkdf2$200000$salt", "password") is False

    def test_rejects_invalid_format_too_many_parts(self):
        assert verify_password_pbkdf2("pbkdf2$200000$salt$hash$extra", "password") is False

    def test_rejects_invalid_hex_salt(self):
        assert verify_password_pbkdf2("pbkdf2$200000$notahex$hash", "password") is False

    def test_rejects_invalid_hex_hash(self):
        assert verify_password_pbkdf2("pbkdf2$200000$aabb$notahex", "password") is False

    def test_rejects_invalid_iterations(self):
        assert verify_password_pbkdf2("pbkdf2$notanumber$aabb$ccdd", "password") is False

    def test_verifies_with_custom_iterations(self):
        stored = hash_password_pbkdf2("mypassword", iterations=50000)
        assert verify_password_pbkdf2(stored, "mypassword") is True

    def test_empty_password_verification(self):
        stored = hash_password_pbkdf2("")
        assert verify_password_pbkdf2(stored, "") is True

    def test_unicode_password(self):
        stored = hash_password_pbkdf2("senha123áéíóú")
        assert verify_password_pbkdf2(stored, "senha123áéíóú") is True

    def test_rejects_empty_stored_string(self):
        assert verify_password_pbkdf2("", "password") is False
