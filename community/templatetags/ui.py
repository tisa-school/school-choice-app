from django import template
from community.localization import text
register=template.Library()
@register.simple_tag
def ui(value): return text(value)
@register.filter(name='ui')
def ui_filter(value): return text(value)
