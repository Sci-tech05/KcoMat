from django import template

register = template.Library()


@register.filter
def split(value, delimiter=','):
    """Split a string by delimiter and return a list. Usage: {{ value|split:"," }}"""
    if value:
        return [item.strip() for item in str(value).split(delimiter) if item.strip()]
    return []


@register.filter
def index(lst, i):
    """Get item at index from list. Usage: {{ mylist|index:0 }}"""
    try:
        return lst[int(i)]
    except (IndexError, TypeError, ValueError):
        return ''


@register.filter
def multiply(value, factor):
    """Multiply value by factor. Usage: {{ price|multiply:1.1 }}"""
    try:
        return int(value) * int(factor)
    except (TypeError, ValueError):
        return 0
