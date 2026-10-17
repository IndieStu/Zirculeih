from datetime import datetime

from django import template

register = template.Library()


@register.filter
def local_label(value):
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.strftime("%d.%m.%Y %H:%M") if "T" in value else parsed.strftime("%d.%m.%Y")
    except (TypeError, ValueError):
        return value
