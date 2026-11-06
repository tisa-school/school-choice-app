"""Small shared UI catalogs for the existing Django and browser presentation architecture."""
import json
from functools import lru_cache
from pathlib import Path
from django.utils import translation
ROOT=Path(__file__).resolve().parent.parent/'content'
ACTIVE_LOCALES={'en':('English','en','en-GB'),'pt-PT':('Português (Portugal)','pt','pt-PT'),'tr':('Türkçe','tr','tr-TR')}
REQUESTED_LOCALES=[('ru','Русский'),('uk','Українська'),('th','ไทย'),('hi-IN','हिन्दी (भारत)'),('he','עברית'),('zh-CN','简体中文'),('zh-TW','繁體中文'),('ja','日本語'),('ko','한국어'),('es-ES','Español (España)'),('pt-BR','Português (Brasil)'),('it','Italiano'),('fr','Français'),('de','Deutsch'),('mn','Монгол'),('es-MX','Español (México)'),('ga','Gaeilge'),('id','Bahasa Indonesia'),('tr','Türkçe')]
@lru_cache(maxsize=8)
def catalog(locale):
    if locale not in ACTIVE_LOCALES: locale='en'
    path=ROOT/'locales'/f'{locale}.json'
    return json.loads(path.read_text()) if path.exists() else {}

def active_locale():
    language=translation.get_language() or 'en'
    if language.startswith('pt') and language!='pt-br': return 'pt-PT'
    return 'tr' if language.startswith('tr') else 'en'

def text(value,locale=None):
    value=str(value)
    return catalog(locale or active_locale()).get(value,value)

class InterfaceLanguageMiddleware:
    def __init__(self,get_response): self.get_response=get_response
    def __call__(self,request):
        supplied=request.GET.get('lang')
        locale=supplied if supplied in ACTIVE_LOCALES else request.COOKIES.get('tkzone_language','en')
        if locale not in ACTIVE_LOCALES: locale='en'
        request.ui_locale=locale
        previous=translation.get_language()
        translation.activate(ACTIVE_LOCALES[locale][1])
        try: response=self.get_response(request)
        finally: translation.activate(previous)
        from django.utils.cache import patch_vary_headers
        patch_vary_headers(response,['Cookie'])
        response['Content-Language']=locale
        if supplied in ACTIVE_LOCALES:
            response.set_cookie('tkzone_language',locale,max_age=31536000,secure=request.is_secure(),httponly=True,samesite='Lax')
        return response

def interface_context(request):
    locale=getattr(request,'ui_locale','en')
    return {'ui_locale':locale,'ui_direction':'ltr','ui_languages':[(code,data[0]) for code,data in ACTIVE_LOCALES.items()],'language_query':[(key,value) for key in request.GET for value in request.GET.getlist(key) if key!='lang'],'ui_catalog':catalog(locale),'ui_intl_locale':ACTIVE_LOCALES[locale][2]}
