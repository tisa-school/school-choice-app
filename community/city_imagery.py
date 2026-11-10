"""Bundled, disclosed AI city illustrations; never evidence of an actual venue."""
from django.templatetags.static import static
from .localization import active_locale


def city_cover(category='', locale=None):
    scene = 'lisbon-riverside' if category in ('Nature', 'Sports', 'Science') else 'lisbon-rooftops'
    pt = (locale or active_locale()) == 'pt-PT'
    description = ('AI-generated Lisbon-inspired riverside illustration' if scene == 'lisbon-riverside'
                   else 'AI-generated illustration inspired by Lisbon rooftops and the Tagus')
    if pt:
        description = ('Ilustração de uma zona ribeirinha inspirada em Lisboa, gerada por IA' if scene == 'lisbon-riverside'
                       else 'Ilustração inspirada nos telhados de Lisboa e no Tejo, gerada por IA')
    return {'small': static(f'community/imagery/{scene}-768.webp'),
            'large': static(f'community/imagery/{scene}-1536.webp'),
            'alt': description,
            'caption': 'Imagem da cidade gerada por IA · não é o local' if pt else 'AI city scene · not the venue'}
