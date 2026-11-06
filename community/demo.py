"""Registration-free Tech Week presentation. No accounts or application records are created."""
import json
from django.conf import settings
from .localization import catalog
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.http import require_safe

@require_safe
def presentation(request, section='home', item=''):
    if section not in {'home','events','activities','detail','family','organizer','creator','saved','finder','calendar','child','crews','admin','safety','about','onboarding'}:
        raise Http404()
    project=json.loads((settings.BASE_DIR/'content/project.json').read_text())
    project['roles']={lang:{person['role']:catalog(lang).get(person['role'],person['role']) for person in project['contributors']} for lang in ('en','pt-PT')}
    response=render(request,'community/demo.html',{'demo_section':section,'demo_item':item,'project_credits':project})
    response['Content-Security-Policy']="default-src 'self'; connect-src 'none'; form-action 'none'; frame-src 'none'; object-src 'none'; base-uri 'none'; img-src 'self' data:; style-src 'self' 'unsafe-inline'"
    response['Cache-Control']='no-store'
    response['X-Robots-Tag']='noindex, nofollow'
    return response
