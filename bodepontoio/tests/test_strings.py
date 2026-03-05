from django.test import SimpleTestCase

from bodepontoio.utils.strings import trim_string


class TestTrimString(SimpleTestCase):

    def test_removes_leading_spaces(self):
        result = trim_string("   texto")
        self.assertEqual(result, "texto")

    def test_removes_trailing_spaces(self):
        result = trim_string("texto   ")
        self.assertEqual(result, "texto")

    def test_removes_multiple_spaces_between_words(self):
        result = trim_string("palavra1    palavra2")
        self.assertEqual(result, "palavra1 palavra2")

    def test_handles_tabs(self):
        result = trim_string("palavra1\t\tpalavra2")
        self.assertEqual(result, "palavra1 palavra2")

    def test_handles_newlines(self):
        result = trim_string("palavra1\n\npalavra2")
        self.assertEqual(result, "palavra1 palavra2")

    def test_handles_mixed_whitespace(self):
        result = trim_string("  palavra1  \t\n  palavra2  ")
        self.assertEqual(result, "palavra1 palavra2")

    def test_empty_string(self):
        result = trim_string("")
        self.assertEqual(result, "")

    def test_only_spaces(self):
        result = trim_string("     ")
        self.assertEqual(result, "")

    def test_single_word(self):
        result = trim_string("palavra")
        self.assertEqual(result, "palavra")

    def test_already_clean_string(self):
        result = trim_string("texto já formatado")
        self.assertEqual(result, "texto já formatado")
