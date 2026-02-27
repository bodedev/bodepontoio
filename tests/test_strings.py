from bodepontoio.utils.strings import trim_string


class TestTrimString:
    def test_removes_leading_spaces(self):
        assert trim_string("   texto") == "texto"

    def test_removes_trailing_spaces(self):
        assert trim_string("texto   ") == "texto"

    def test_removes_multiple_spaces_between_words(self):
        assert trim_string("palavra1    palavra2") == "palavra1 palavra2"

    def test_handles_tabs(self):
        assert trim_string("palavra1\t\tpalavra2") == "palavra1 palavra2"

    def test_handles_newlines(self):
        assert trim_string("palavra1\n\npalavra2") == "palavra1 palavra2"

    def test_handles_mixed_whitespace(self):
        assert trim_string("  palavra1  \t\n  palavra2  ") == "palavra1 palavra2"

    def test_empty_string(self):
        assert trim_string("") == ""

    def test_only_spaces(self):
        assert trim_string("     ") == ""

    def test_single_word(self):
        assert trim_string("palavra") == "palavra"

    def test_already_clean_string(self):
        assert trim_string("texto já formatado") == "texto já formatado"
