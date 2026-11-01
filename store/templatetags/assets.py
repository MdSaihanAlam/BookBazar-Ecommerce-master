import os

from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def versioned_static(path):
    """Static URL with the file's modification time appended, so browsers fetch it again after it changes."""
    url = static(path)
    found = finders.find(path)
    if found:
        url += f"?v={int(os.path.getmtime(found))}"
    return url
