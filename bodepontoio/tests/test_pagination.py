from django.core.paginator import EmptyPage, PageNotAnInteger
from django.test import SimpleTestCase

from bodepontoio.utils.pagination import LastPageFixPaginator


class TestLastPageFixPaginator(SimpleTestCase):

    def setUp(self):
        self.items = list(range(1, 101))  # 100 items
        self.paginator = LastPageFixPaginator(self.items, 10)  # 10 per page = 10 pages

    def test_valid_page_number(self):
        result = self.paginator.validate_number(5)
        self.assertEqual(result, 5)

    def test_first_page(self):
        result = self.paginator.validate_number(1)
        self.assertEqual(result, 1)

    def test_last_page(self):
        result = self.paginator.validate_number(10)
        self.assertEqual(result, 10)

    def test_page_greater_than_num_pages_returns_last_page(self):
        result = self.paginator.validate_number(15)
        self.assertEqual(result, 10)

    def test_page_much_greater_than_num_pages_returns_last_page(self):
        result = self.paginator.validate_number(1000)
        self.assertEqual(result, 10)

    def test_page_zero_raises_empty_page(self):
        with self.assertRaises(EmptyPage) as context:
            self.paginator.validate_number(0)
        self.assertEqual(str(context.exception), "That page number is less than 1")

    def test_negative_page_raises_empty_page(self):
        with self.assertRaises(EmptyPage) as context:
            self.paginator.validate_number(-1)
        self.assertEqual(str(context.exception), "That page number is less than 1")

    def test_string_number_is_converted(self):
        result = self.paginator.validate_number("5")
        self.assertEqual(result, 5)

    def test_non_integer_string_raises_page_not_an_integer(self):
        with self.assertRaises(PageNotAnInteger) as context:
            self.paginator.validate_number("abc")
        self.assertEqual(str(context.exception), "That page number is not an integer")

    def test_none_raises_page_not_an_integer(self):
        with self.assertRaises(PageNotAnInteger) as context:
            self.paginator.validate_number(None)
        self.assertEqual(str(context.exception), "That page number is not an integer")

    def test_float_string_raises_page_not_an_integer(self):
        with self.assertRaises(PageNotAnInteger) as context:
            self.paginator.validate_number("2.5")
        self.assertEqual(str(context.exception), "That page number is not an integer")

    def test_get_page_returns_last_page_for_out_of_range(self):
        page = self.paginator.get_page(15)
        self.assertEqual(page.number, 10)

    def test_pagination_works_correctly(self):
        page = self.paginator.get_page(1)
        self.assertEqual(list(page.object_list), list(range(1, 11)))

        page = self.paginator.get_page(10)
        self.assertEqual(list(page.object_list), list(range(91, 101)))
