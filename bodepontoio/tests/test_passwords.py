from django.test import SimpleTestCase

from bodepontoio.utils.passwords.generate_hash import (
    hash_password_pbkdf2,
    verify_password_pbkdf2,
)


class TestHashPasswordPbkdf2(SimpleTestCase):

    def test_generates_hash_with_correct_format(self):
        result = hash_password_pbkdf2("mypassword")
        parts = result.split("$")
        self.assertEqual(len(parts), 4)
        self.assertEqual(parts[0], "pbkdf2")
        self.assertEqual(parts[1], "200000")  # default iterations

    def test_generates_different_hashes_for_same_password(self):
        # Due to random salt, same password should generate different hashes
        hash1 = hash_password_pbkdf2("mypassword")
        hash2 = hash_password_pbkdf2("mypassword")
        self.assertNotEqual(hash1, hash2)

    def test_custom_iterations(self):
        result = hash_password_pbkdf2("mypassword", iterations=100000)
        parts = result.split("$")
        self.assertEqual(parts[1], "100000")

    def test_raises_type_error_for_non_string(self):
        with self.assertRaises(TypeError) as context:
            hash_password_pbkdf2(12345)
        self.assertEqual(str(context.exception), "password deve ser uma string")

    def test_raises_type_error_for_none(self):
        with self.assertRaises(TypeError):
            hash_password_pbkdf2(None)

    def test_empty_password(self):
        result = hash_password_pbkdf2("")
        parts = result.split("$")
        self.assertEqual(len(parts), 4)
        self.assertEqual(parts[0], "pbkdf2")


class TestVerifyPasswordPbkdf2(SimpleTestCase):

    def test_verifies_correct_password(self):
        stored = hash_password_pbkdf2("mypassword")
        self.assertTrue(verify_password_pbkdf2(stored, "mypassword"))

    def test_rejects_incorrect_password(self):
        stored = hash_password_pbkdf2("mypassword")
        self.assertFalse(verify_password_pbkdf2(stored, "wrongpassword"))

    def test_rejects_invalid_format_wrong_prefix(self):
        self.assertFalse(verify_password_pbkdf2("invalid$200000$salt$hash", "password"))

    def test_rejects_invalid_format_missing_parts(self):
        self.assertFalse(verify_password_pbkdf2("pbkdf2$200000$salt", "password"))

    def test_rejects_invalid_format_too_many_parts(self):
        self.assertFalse(verify_password_pbkdf2("pbkdf2$200000$salt$hash$extra", "password"))

    def test_rejects_invalid_hex_salt(self):
        self.assertFalse(verify_password_pbkdf2("pbkdf2$200000$notahex$hash", "password"))

    def test_rejects_invalid_hex_hash(self):
        self.assertFalse(verify_password_pbkdf2("pbkdf2$200000$aabb$notahex", "password"))

    def test_rejects_invalid_iterations(self):
        self.assertFalse(verify_password_pbkdf2("pbkdf2$notanumber$aabb$ccdd", "password"))

    def test_verifies_with_custom_iterations(self):
        stored = hash_password_pbkdf2("mypassword", iterations=50000)
        self.assertTrue(verify_password_pbkdf2(stored, "mypassword"))

    def test_empty_password_verification(self):
        stored = hash_password_pbkdf2("")
        self.assertTrue(verify_password_pbkdf2(stored, ""))

    def test_unicode_password(self):
        stored = hash_password_pbkdf2("senha123áéíóú")
        self.assertTrue(verify_password_pbkdf2(stored, "senha123áéíóú"))

    def test_rejects_empty_stored_string(self):
        self.assertFalse(verify_password_pbkdf2("", "password"))
