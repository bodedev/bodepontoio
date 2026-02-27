import pytest
from django.core.paginator import EmptyPage, PageNotAnInteger

from bodepontoio.utils.pagination import LastPageFixPaginator


class TestLastPageFixPaginator:
    def setup_method(self):
        self.items = list(range(1, 101))  # 100 items
        self.paginator = LastPageFixPaginator(self.items, 10)  # 10 per page = 10 pages

    def test_valid_page_number(self):
        assert self.paginator.validate_number(5) == 5

    def test_first_page(self):
        assert self.paginator.validate_number(1) == 1

    def test_last_page(self):
        assert self.paginator.validate_number(10) == 10

    def test_page_greater_than_num_pages_returns_last_page(self):
        assert self.paginator.validate_number(15) == 10

    def test_page_much_greater_than_num_pages_returns_last_page(self):
        assert self.paginator.validate_number(1000) == 10

    def test_page_zero_raises_empty_page(self):
        with pytest.raises(EmptyPage, match="That page number is less than 1"):
            self.paginator.validate_number(0)

    def test_negative_page_raises_empty_page(self):
        with pytest.raises(EmptyPage, match="That page number is less than 1"):
            self.paginator.validate_number(-1)

    def test_string_number_is_converted(self):
        assert self.paginator.validate_number("5") == 5

    def test_non_integer_string_raises_page_not_an_integer(self):
        with pytest.raises(PageNotAnInteger, match="That page number is not an integer"):
            self.paginator.validate_number("abc")

    def test_none_raises_page_not_an_integer(self):
        with pytest.raises(PageNotAnInteger, match="That page number is not an integer"):
            self.paginator.validate_number(None)

    def test_float_string_raises_page_not_an_integer(self):
        with pytest.raises(PageNotAnInteger, match="That page number is not an integer"):
            self.paginator.validate_number("2.5")

    def test_get_page_returns_last_page_for_out_of_range(self):
        page = self.paginator.get_page(15)
        assert page.number == 10

    def test_pagination_works_correctly(self):
        page = self.paginator.get_page(1)
        assert list(page.object_list) == list(range(1, 11))

        page = self.paginator.get_page(10)
        assert list(page.object_list) == list(range(91, 101))
