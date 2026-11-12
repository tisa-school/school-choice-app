"""Shared server/browser interface catalogs; authored content and names retain their original text."""
import json,re
from functools import lru_cache
from pathlib import Path
from django.utils import translation
ROOT=Path(__file__).resolve().parent.parent/'content'
ACTIVE_LOCALES={
'en':('English','en','en-GB'),'zh-CN':('中文（普通话）','zh-hans','zh-CN'),'hi':('हिन्दी','hi','hi-IN'),'es':('Español','es','es-ES'),'ar':('العربية','ar','ar'),'fr':('Français','fr','fr-FR'),'bn':('বাংলা','bn','bn-BD'),'pt-PT':('Português (Portugal)','pt','pt-PT'),'ru':('Русский','ru','ru-RU'),'ur':('اردو','ur','ur-PK'),'tr':('Türkçe','tr','tr-TR')}
REQUESTED_LOCALES=[]
ALIASES={'hi-IN':'hi','es-ES':'es','es-MX':'es','pt':'pt-PT','zh':'zh-CN','zh-hans':'zh-CN'}

@lru_cache(maxsize=32)
def catalog(locale):
    if locale not in ACTIVE_LOCALES:locale='en'
    return json.loads((ROOT/'locales'/f'{locale}.json').read_text())

def active_locale():
    language=translation.get_language() or 'en'
    return next((locale for locale,config in ACTIVE_LOCALES.items() if config[1]==language),'en')

@lru_cache(maxsize=1)
def patterns():
    result=[]
    for key in catalog('en'):
        if re.search(r'\{value\d+\}',key):
            parts=re.split(r'(\{value\d+\})',key)
            pattern=''.join('(?P<'+part[1:-1]+'>.*?)' if re.fullmatch(r'\{value\d+\}',part) else re.escape(part) for part in parts)
            try:result.append((re.compile('^'+pattern+'$',re.S),key))
            except re.error:pass
    return result

def text(value,locale=None):
    value=str(value);dictionary=catalog(locale or active_locale())
    if value in dictionary:return dictionary[value]
    if value.startswith('Organizer application '):
        suffix=value[len('Organizer application '):]
        if suffix in ['approved','declined']:return dictionary.get('Organizer application','Organizer application')+' '+dictionary.get(suffix.title(),suffix.title())
    for expression,key in patterns():
        match=expression.fullmatch(value)
        if match:
            try:
                values=match.groupdict()
                if key=='Ticket {value0}':values['value0']=dictionary.get(values['value0'],values['value0'])
                if key=='{value0}: {value1}.':values['value1']=dictionary.get(values['value1'],values['value1'])
                return dictionary.get(key,key).format_map(values)
            except (ValueError,KeyError):return value
    return value

class InterfaceLanguageMiddleware:
    def __init__(self,get_response):self.get_response=get_response
    def __call__(self,request):
        if request.path=='/health/':return self.get_response(request)
        from .models import InterfacePreference,SiteConfiguration
        request.site_configuration=SiteConfiguration.objects.filter(pk=1).first()
        default_language=request.site_configuration.default_language if request.site_configuration else 'en'
        supplied=ALIASES.get(request.GET.get('lang'),request.GET.get('lang'))
        stored=InterfacePreference.objects.filter(user=request.user).values_list('language',flat=True).first() if request.user.is_authenticated else None
        locale=supplied if supplied in ACTIVE_LOCALES else stored or request.COOKIES.get('tkzone_language',default_language)
        if locale not in ACTIVE_LOCALES:locale='en'
        request.ui_locale=locale;previous=translation.get_language();translation.activate(ACTIVE_LOCALES[locale][1])
        try:
            response=self.get_response(request)
            if not response.streaming and 'text/html' in response.get('Content-Type',''):
                from .html_localization import localize_html
                source=response.content.decode(response.charset)
                cache={}
                def translated(value):
                    if value not in cache:cache[value]=text(value,locale)
                    return cache[value]
                response.content=localize_html(source,translated)
                if response.has_header('Content-Length'):response['Content-Length']=str(len(response.content))
        finally:translation.activate(previous)
        from django.utils.cache import patch_vary_headers
        patch_vary_headers(response,['Cookie'])
        response['Content-Language']=locale
        if request.user.is_authenticated:response['Cache-Control']='private, no-store'
        if supplied in ACTIVE_LOCALES:
            response.set_cookie('tkzone_language',locale,max_age=31536000,secure=request.is_secure(),httponly=True,samesite='Lax')
        if request.user.is_authenticated and request.path not in ['/tour/','/manage/tour/'] and (supplied in ACTIVE_LOCALES or not stored):InterfacePreference.objects.update_or_create(user=request.user,defaults={'language':locale})
        return response

def interface_context(request):
    locale=getattr(request,'ui_locale','en')
    return {'ui_locale':locale,'ui_direction':'rtl' if locale in ['ar','ur'] else 'ltr','ui_languages':[(code,data[0]) for code,data in ACTIVE_LOCALES.items()],'language_query':[(key,value) for key in request.GET for value in request.GET.getlist(key) if key!='lang'],'ui_catalog':catalog(locale),'ui_intl_locale':ACTIVE_LOCALES[locale][2]}
