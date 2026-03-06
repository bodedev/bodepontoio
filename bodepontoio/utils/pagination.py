from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator


class LastPageFixPaginator(Paginator):

    def validate_number(self, number):
        try:
            number = int(number)
        except (TypeError, ValueError):
            raise PageNotAnInteger('That page number is not an integer')
        if number < 1:
            raise EmptyPage('That page number is less than 1')
        if number > self.num_pages:
            return self.num_pages
        return number
