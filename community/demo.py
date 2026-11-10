"""Registration-free school project presentation. No accounts or application records are created."""
import json
from django.conf import settings
from .localization import catalog, ACTIVE_LOCALES
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import render
from django.views.decorators.http import require_safe

@require_safe
def presentation(request, section='home', item=''):
    if section not in {'home','events','activities','detail','family','organizer','creator','saved','finder','calendar','child','crews','admin','safety','about','onboarding'}:
        raise Http404()
    from .demo_access import access_for
    access=access_for(request.user)
    required='organizer' if section in {'organizer','creator'} else 'admin' if section=='admin' else None
    if required and required not in access['roles']:
        return HttpResponseForbidden('This workspace is not available for your account role.')
    project=json.loads((settings.BASE_DIR/'content/project.json').read_text())
    from .team import prepare_team
    prepare_team(request.user,project,request)
    from .city_imagery import city_cover
    project['demo_access']=access
    project['activity_imagery']={'city':city_cover('Arts',request.ui_locale),'river':city_cover('Nature',request.ui_locale)}
    project['roles']={lang:{person['role']:catalog(lang).get(person['role'],person['role']) for person in project['contributors']} for lang in ACTIVE_LOCALES}
    response=render(request,'community/demo.html',{'demo_section':section,'demo_item':item,'project_credits':project,'ai_match_enabled':bool(settings.ANTHROPIC_API_KEY)})
    response['Content-Security-Policy']="default-src 'self'; connect-src 'self'; form-action 'none'; frame-src 'none'; object-src 'none'; base-uri 'none'; img-src 'self' data:; style-src 'self' 'unsafe-inline'"
    if any(person.get('upload_html') for person in project['contributors']):
        response['Content-Security-Policy']=response['Content-Security-Policy'].replace("form-action 'none'", "form-action 'self'")
    response['Cache-Control']='no-store'
    response['X-Robots-Tag']='noindex, nofollow'
    return response
