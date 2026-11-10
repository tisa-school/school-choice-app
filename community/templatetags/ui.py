from django import template
from community.localization import text
register=template.Library()
@register.simple_tag
def ui(value): return text(value)
@register.filter(name='ui')
def ui_filter(value): return text(value)

@register.simple_tag
def activity_cover(event):
    from community.activity_imagery import activity_cover as cover
    return cover(event)
