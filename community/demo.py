"""Compatibility for previously shared URLs; all actions use the live application."""
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_safe

@require_safe
def presentation(request, section='home', item=''):
    targets={'home':'home','events':'events','activities':'activities','family':'family',
             'organizer':'organizer','creator':'organizer_new','saved':'saved',
             'finder':'finder','calendar':'calendar','child':'family','crews':'family',
             'admin':'staff','safety':'about','about':'about','onboarding':'parent_setup'}
    if section=='about':
        from .project_pages import about
        return about(request)
    if section=='detail':
        destination=reverse('detail',args=[int(item)]) if item.isdigit() else reverse('events')
    elif section in targets:destination=reverse(targets[section])
    else:raise Http404()
    query=request.GET.urlencode()
    response=redirect(destination+('?' + query if query else ''))
    response['Cache-Control']='no-store'
    return response
