from decimal import Decimal

from django import template

from bodepontoio.utils.numbers import grana

register = template.Library()


@register.filter(name='grana')
def grana_filter(valor, prefixo=None):
    """Aplica a função de grana para os valores do template."""
    return grana(valor, prefixo)


@register.simple_tag
def url_replace(request, field, value):
    dict_ = request.GET.copy()
    dict_[field] = value
    return dict_.urlencode()


@register.filter
def multiply(value, arg):
    return value * arg


@register.filter
def roi(value, arg):
    return ((Decimal(value) - arg) / arg) * 100
