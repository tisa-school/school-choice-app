"""Conservative, local image selection from actual listing details, never city-only fallbacks."""
import json
import re
import unicodedata
from functools import lru_cache
from django.conf import settings
from django.templatetags.static import static
from django.urls import reverse
from .localization import active_locale


@lru_cache(maxsize=1)
def specification():
    return json.loads((settings.BASE_DIR/'content/activity-imagery.json').read_text())


def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFD',str(value or '').lower()) if not unicodedata.combining(c))


def contains(text, term):
    return re.search(r'(?<![a-z0-9])'+re.escape(normalized(term)), text) is not None


def choose_scene(details, spec=None):
    scenes=(spec or specification())['scenes']
    title=normalized(details.get('title'));description=normalized(details.get('description'))
    venue=normalized(details.get('venue'));area=normalized(details.get('area'))
    context=' '.join([title,description,venue,area])
    if not any(contains(context,word) for word in ['Lisbon','Lisboa','Alfama','Belém','Graça','Estrela','Alvalade','Campo de Ourique','Parque das Nações']):
        return None
    setting=details.get('activityEnvironment') or 'unspecified'
    inside=any(contains(venue,w) for w in ['room','hall','studio','classroom','library','lab','sala','auditorio'])
    outside=any(contains(venue,w) for w in ['park','garden','pitch','field','parque','jardim','campo'])
    venue_setting='indoor' if inside and not outside else 'outdoor' if outside and not inside else 'unspecified'
    if setting in ['indoor','outdoor'] and venue_setting in ['indoor','outdoor'] and setting!=venue_setting:return None
    if setting not in ['indoor','outdoor','mixed']:
        setting=venue_setting
        if setting=='unspecified':
            text=title+' '+description
            inside=any(contains(text,w) for w in ['indoor','in a studio','in the studio','numa sala'])
            outside=any(contains(text,w) for w in ['outdoor','in a park','in the park','ao ar livre'])
            setting='indoor' if inside and not outside else 'outdoor' if outside and not inside else 'unspecified'
    low,high=details.get('minAge'),details.get('maxAge')
    if type(low) is not int or type(high) is not int or setting=='unspecified':return None
    ranked=[]
    for key,scene in scenes.items():
        if details.get('interest') not in scene['categories'] or low>scene['minAge'] or high<scene['maxAge']:continue
        if scene['setting']!=setting:continue
        text=title+' '+description
        if any(contains(text,w) for w in scene['exclude']):continue
        score=sum(4*contains(title,w)+2*contains(description,w) for w in scene['keywords'])
        if score:ranked.append((score,key))
    return sorted(ranked,key=lambda x:(-x[0],x[1]))[0][1] if ranked else None


def manifest(locale=None):
    locale='pt-PT' if (locale or active_locale())=='pt-PT' else 'en'
    spec=specification()
    return {**spec,'scenes':{key:{**scene,'small':static(f"community/imagery/{scene['file']}-768.webp"),'large':static(f"community/imagery/{scene['file']}-1536.webp"),'description':scene['alt'][locale]} for key,scene in spec['scenes'].items()}}


def activity_cover(event):
    pt=active_locale()=='pt-PT'
    if getattr(event,'image_is_reviewed',False):
        source=event.image_source
        caption=({'event':'Fotografia deste evento · fornecida pelo organizador','stock':'Imagem de arquivo ilustrativa · não é este evento','generated':'Ilustração IA · não é este evento'} if pt else {'event':'Organiser-supplied photo of this event','stock':'Illustrative stock image · not this event','generated':'AI illustration · not this event'})[source]
        return {'small':reverse('private_media',args=['event',event.pk]),'alt':event.image_alt,'caption':caption,'kind':'upload'}
    details={'title':event.title,'description':event.description,'minAge':event.min_age,'maxAge':event.max_age,'interest':event.category,'venue':event.venue,'area':event.area,'activityEnvironment':event.activity_environment}
    key=choose_scene(details)
    if not key:return {'kind':'placeholder','alt':'Imagem de atividade a aguardar revisão' if pt else 'Activity image awaiting a suitable match','caption':'Imagem a aguardar revisão' if pt else 'Image awaiting review'}
    scene=manifest()['scenes'][key]
    return {**scene,'kind':'illustration','alt':('Ilustração IA: ' if pt else 'AI illustration: ')+scene['description'],'caption':'Ilustração IA · não é este evento' if pt else 'AI illustration · not this event'}
