from django.test import SimpleTestCase

from bodepontoio.utils.strings import split_name, trim_string


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


class TestSplitName(SimpleTestCase):

    def test_splits_full_name_with_multiple_parts(self):
        result = split_name("João da Silva Pedroso")
        self.assertEqual(result, ("João", "da Silva Pedroso"))

    def test_splits_first_and_last_name(self):
        result = split_name("Maria Silva")
        self.assertEqual(result, ("Maria", "Silva"))

    def test_single_name_returns_empty_rest(self):
        result = split_name("Maria")
        self.assertEqual(result, ("Maria", ""))

    def test_strips_leading_and_trailing_spaces(self):
        result = split_name("  Pedro   Santos  ")
        self.assertEqual(result, ("Pedro", "Santos"))

    def test_preserves_internal_multiple_spaces_in_rest(self):
        result = split_name("Ana   Maria   Souza")
        self.assertEqual(result, ("Ana", "Maria   Souza"))

    def test_empty_string_raises_index_error(self):
        with self.assertRaises(IndexError):
            split_name("")

    def test_only_whitespace_raises_index_error(self):
        with self.assertRaises(IndexError):
            split_name("     ")

    def test_handles_tabs_as_separator(self):
        result = split_name("João\tda Silva")
        self.assertEqual(result, ("João", "da Silva"))

    def test_handles_newlines_as_separator(self):
        result = split_name("João\nda Silva")
        self.assertEqual(result, ("João", "da Silva"))

    def test_preserves_accented_characters(self):
        result = split_name("José Ávila Gonçalves")
        self.assertEqual(result, ("José", "Ávila Gonçalves"))

    def test_preserves_case(self):
        result = split_name("ANA maria SILVA")
        self.assertEqual(result, ("ANA", "maria SILVA"))

    def test_returns_tuple(self):
        result = split_name("João Silva")
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
