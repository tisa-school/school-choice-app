"""Attach approved, visible team portraits without exposing private image URLs to guests."""
from django.urls import reverse


def canonical_team_text(value):
    return value.replace('Sophia Gateneo','Sophia Gatenyo')


def person_names(person):
    name=person['public_name']
    return [name,'Sophia Gateneo'] if name=='Sophia Gatenyo' else [name]


def project_school(project):
    from .models import SiteConfiguration,School
    config=SiteConfiguration.objects.select_related('project_school').filter(pk=1).first()
    if config and config.project_school_id:return config.project_school
    schools=list(School.objects.filter(name__iexact=project['school'])[:2])
    return schools[0] if len(schools)==1 else None


def prepare_team(user, project, request=None):
    from .community_views import team_visible, moderator
    from .discovery import membership
    from django.template.loader import render_to_string
    member=membership(user)
    school=project_school(project)
    can_upload=bool(school and moderator(user,school.pk))
    names=[name for person in project['contributors'] for name in person_names(person)]
    portraits={}
    photos=team_visible(user).filter(school=school,name__in=names,is_group=False).order_by('-created_at','-pk')
    for photo in photos:
        portraits.setdefault(canonical_team_text(photo.name),photo)
    for person in project['contributors']:
        photo=portraits.get(person['public_name'])
        if photo:
            person['photo']={'url':reverse('protected_photo',args=['team',photo.pk]),'description':canonical_team_text(photo.description)}
        if can_upload and request is not None:
            person['upload_html']=render_to_string('community/team_inline_upload.html',{'person':person},request=request)
    return project
