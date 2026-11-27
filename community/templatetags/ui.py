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

@register.filter
def event_text(event,field):
    if field not in ('title','description'):return ''
    from community.localization import active_locale
    translations=getattr(event,'translations',{})
    candidate=translations.get(active_locale(),{}) if isinstance(translations,dict) else {}
    return candidate.get(field) or getattr(event,field,'') if isinstance(candidate,dict) else getattr(event,field,'')

@register.simple_tag
def money(value):
    from django.utils.formats import number_format
    from community.localization import active_locale
    number=number_format(value,decimal_pos=2,use_l10n=True)
    from django.utils.html import format_html
    return format_html('<span data-ui-currency="{}">{}</span>',str(value),('€'+number) if active_locale()=='en' else number+' €')
