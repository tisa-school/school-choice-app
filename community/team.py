"""Attach approved, visible team portraits without exposing private image URLs to guests."""
from django.urls import reverse


def prepare_team(user, project, request=None):
    from .community_views import team_visible, moderator
    from .discovery import membership
    from django.template.loader import render_to_string
    member=membership(user)
    can_upload=moderator(user) and (user.is_superuser or (member and member.school.name.casefold()==project["school"].casefold()))
    names=[person['public_name'] for person in project['contributors']]
    portraits={}
    photos=team_visible(user).filter(school__name__iexact=project['school'],name__in=names,is_group=False).order_by('-created_at','-pk')
    for photo in photos:
        portraits.setdefault(photo.name,photo)
    for person in project['contributors']:
        photo=portraits.get(person['public_name'])
        if photo:
            person['photo']={'url':reverse('protected_photo',args=['team',photo.pk]),'description':photo.description,'visibility':photo.visibility}
        if can_upload and request is not None:
            person['upload_html']=render_to_string('community/team_inline_upload.html',{'person':person},request=request)
    return project
