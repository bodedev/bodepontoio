from django.db.models import Func


class Round(Func):
    function = 'ROUND'
    template = '%(function)s(%(expressions)s, 2)'
