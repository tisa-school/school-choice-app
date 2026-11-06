"""Attach approved, visible team portraits without exposing private image URLs to guests."""
from django.urls import reverse


def prepare_team(user, project):
    from .community_views import team_visible
    names=[person['public_name'] for person in project['contributors']]
    portraits={}
    photos=team_visible(user).filter(school__name__iexact=project['school'],name__in=names,is_group=False).order_by('-created_at','-pk')
    for photo in photos:
        portraits.setdefault(photo.name,photo)
    for person in project['contributors']:
        photo=portraits.get(person['public_name'])
        if photo:
            person['photo']={'url':reverse('protected_photo',args=['team',photo.pk]),'description':photo.description}
        if person['group']=='students':person['public_name']=person['public_name'].split()[0]
    return project
