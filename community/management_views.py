"""Verified school administrators stay scoped; super administrators have global access."""
import json
from functools import wraps
from uuid import uuid4
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.http import Http404,HttpResponseForbidden
from django.shortcuts import render,get_object_or_404,redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST
from .models import School,Membership,ParentAccount,ChildProfile,SchoolProfile,Event,ExperienceListing,SchoolMedia,TeamPhoto,PlatformAudit,SiteConfiguration,Feedback,ExperienceReport,OrganizerApplication
from .discovery import discovery_view,membership
from .community_views import moderator
from .management_forms import ManagedUserForm,ManagedEventForm,ExperienceForm,SchoolProfileForm,SchoolMediaForm,SiteConfigurationForm,PrivateChildForm
from .forms import ChildProfileForm
from .community_forms import PortraitCropForm
from .localization import text


def audit(request,action,entity,school=None,fields=()):
    member=getattr(request,'member',None) or membership(request.user)
    return PlatformAudit.objects.create(actor=request.user,school=school or (member.school if member else None),action=action,entity_type=entity.__class__.__name__,entity_id=str(entity.pk),changed_fields=[str(k) for k in fields if k not in ['password','current_password']])

def administrator(view):
    @login_required
    @discovery_view
    @wraps(view)
    def wrapped(request,*args,**kwargs):
        if not moderator(request.user):return HttpResponseForbidden('An authorised administrator account is required.')
        return view(request,*args,**kwargs)
    return wrapped


def scoped_records(request,kind):
    school=request.member.school if request.member else None
    global_access=request.user.is_superuser
    if kind=='users':return User.objects.all() if global_access else User.objects.filter(membership__school=school)
    if kind=='families':return ParentAccount.objects.select_related('user').all() if global_access else ParentAccount.objects.select_related('user').filter(user__membership__school=school)
    if kind=='children':return ChildProfile.objects.select_related('parent__user').all() if global_access else ChildProfile.objects.select_related('parent__user').filter(parent__user__membership__school=school)
    if kind=='schools':return SchoolProfile.objects.all() if global_access else SchoolProfile.objects.filter(school=school)
    if kind=='activities':return Event.objects.all() if global_access else Event.objects.filter(school=school)
    if kind=='experiences':return ExperienceListing.objects.all() if global_access else ExperienceListing.objects.filter(school=school)
    if kind=='organisers':return OrganizerApplication.objects.select_related('user','school').all() if global_access else OrganizerApplication.objects.select_related('user','school').filter(school=school)
    if kind=='media':return TeamPhoto.objects.all() if global_access else TeamPhoto.objects.filter(school=school)
    if kind=='reports':return Feedback.objects.all() if global_access else Feedback.objects.filter(school=school)
    if kind=='audit':return PlatformAudit.objects.select_related('actor').all() if global_access else PlatformAudit.objects.select_related('actor').filter(school=school)
    raise Http404()

KINDS={'users':'Users','families':'Families','children':'Child profiles','schools':'Schools','activities':'Activities and events','experiences':'Venues and experiences','organisers':'Organisers','media':'Photos and media','reports':'Reports','audit':'Audit log'}

@administrator
def dashboard(request):
    return render(request,'management/dashboard.html',{'management_sections':[(key,label,scoped_records(request,key).count()) for key,label in KINDS.items()]})

@administrator
def records(request,kind):
    if kind not in KINDS:raise Http404()
    query=scoped_records(request,kind)
    q=request.GET.get('q','').strip()[:150]
    field={'users':'username','families':'user__username','children':'nickname','schools':'name','activities':'title','experiences':'title','organisers':'organization','media':'name','reports':'message','audit':'action'}[kind]
    if q:query=query.filter(**{field+'__icontains':q})
    from django.core.paginator import Paginator
    page=Paginator(query.order_by('-pk'),30).get_page(request.GET.get('page'))
    rows=[]
    for item in page:
        label=getattr(item,'title',None) or getattr(item,'nickname',None) or getattr(item,'name',None) or getattr(item,'organization',None) or (item.user.get_full_name() or item.user.username if kind=='families' else str(item))
        if kind=='audit':label=f'{item.created_at:%d %b %Y %H:%M} · {item.action} · {item.entity_type} #{item.entity_id}'
        if kind=='reports':label=f'{item.get_kind_display()} · {item.status} · {item.message[:100]}'
        edit=reverse('management_edit',args=[kind,item.pk]) if kind in ['users','children','schools','activities','experiences'] else ''
        if kind=='families':edit=reverse('management_family_detail',args=[item.pk])
        if kind=='media':edit=reverse('team_photo_edit',args=[item.pk])
        if kind=='organisers':edit=reverse('management_review',args=[kind,item.pk])
        if kind=='reports':edit=reverse('management_review',args=[kind,item.pk])
        rows.append({'item':item,'label':label,'edit_url':edit,'status':getattr(item,'status',None) or ('Published' if getattr(item,'is_published',False) else '')})
    return render(request,'management/records.html',{'kind':kind,'management_title':KINDS[kind],'rows':rows,'page_obj':page,'can_create':kind in ['schools','activities','experiences'],'q':q})

@administrator
@transaction.atomic
def edit(request,kind,pk=None):
    if kind not in ['users','children','schools','activities','experiences']:raise Http404()
    if pk is None and kind not in ['schools','activities','experiences']:raise Http404()
    item=get_object_or_404(scoped_records(request,kind).select_for_update(),pk=pk) if pk else {'schools':SchoolProfile,'activities':Event,'experiences':ExperienceListing}[kind]()
    if not pk:
        if kind=='schools':item.school=request.member.school if request.member else None
        else:item.created_by=request.user;item.school=request.member.school if request.member else None
    Form={'users':ManagedUserForm,'children':PrivateChildForm,'schools':SchoolProfileForm,'activities':ManagedEventForm,'experiences':ExperienceForm}[kind]
    kwargs={'actor':request.user} if kind=='users' else {'actor':request.user,'member':request.member} if kind=='activities' else {}
    if not pk and kind=='schools' and not request.user.is_superuser and scoped_records(request,'schools').exists():return redirect('management_edit',kind='schools',pk=scoped_records(request,'schools').first().pk)
    form=Form(request.POST or None,request.FILES or None,instance=item,**kwargs)
    if request.method=='POST' and form.is_valid():
        obj=form.save(commit=False)
        if kind in ['schools','experiences'] and not obj.slug:obj.slug=slugify(obj.name if kind=='schools' else obj.title)[:140]+'-'+uuid4().hex[:8]
        if kind=='activities' and obj.status=='published':obj.published_by=request.user;obj.published_at=timezone.now()
        if kind=='activities' and obj.status=='draft':obj.published_by=None
        obj.save();audit(request,'content.updated' if pk else 'content.created',obj,school=getattr(obj,'school',None),fields=form.changed_data)
        from .persistence import saved_success
        saved_success(request,'Changes saved.');return redirect('management_records',kind=kind)
    return render(request,'management/edit.html',{'form':form,'management_title':KINDS[kind],'kind':kind,'record':item,'can_delete':pk and kind in ['schools','activities','experiences'],'school_profile':item if kind=='schools' else None})

@administrator
@require_POST
@transaction.atomic
def content_action(request,kind,pk):
    if kind not in ['schools','activities','experiences']:raise Http404()
    item=get_object_or_404(scoped_records(request,kind).select_for_update(),pk=pk);action=request.POST.get('action')
    if action=='delete':
        expected=str(getattr(item,'name',getattr(item,'title','')))
        if request.POST.get('confirm')!=expected:messages.error(request,text('Type the exact title to confirm deletion.'));return redirect('management_edit',kind=kind,pk=pk)
        if kind=='activities' and (item.status=='published' or item.participations.exists() or item.requests.exists() or item.family_bookings.exists() or item.familyplan_set.exists()):messages.error(request,text('Unpublish or cancel this activity through its existing request workflow; records with requests cannot be deleted here.'));return redirect('management_edit',kind=kind,pk=pk)
        audit(request,'content.deleted',item,school=getattr(item,'school',None));item.delete();return redirect('management_records',kind=kind)
    if action not in ['publish','unpublish','archive']:raise Http404()
    if kind=='activities':
        item.archived=action=='archive'
        item.status='published' if action=='publish' else 'draft';item.published_by=request.user if action=='publish' else None
        if action=='publish':item.published_at=timezone.now()
    else:item.is_published=action=='publish'
    if kind in ['schools','experiences']:item.archived=action=='archive'
    try:
        if action=='publish':item.full_clean()
    except ValidationError as error:messages.error(request,' '.join(error.messages));return redirect('management_edit',kind=kind,pk=pk)
    item.save();audit(request,'content.'+action,item,school=getattr(item,'school',None));messages.success(request,text('Changes saved.'));return redirect('management_records',kind=kind)

@administrator
def team_profile(request,person_id):
    from .team import prepare_team,project_school
    project=json.loads((settings.BASE_DIR/'content/project.json').read_text());school=project_school(project)
    if school is not None and not moderator(request.user,school.pk):raise Http404()
    person=next((p for p in project['contributors'] if p['id']==person_id),None)
    if person is None:raise Http404()
    prepare_team(request.user,project,request)
    return render(request,'management/portrait.html',{'person':person,'portrait_form':PortraitCropForm(),'missing_school':school is None})

@administrator
def team_profiles(request):
    project=json.loads((settings.BASE_DIR/'content/project.json').read_text())
    return render(request,'management/team_profiles.html',{'roster':project['contributors']})

@administrator
def site_settings(request):
    if not request.user.is_superuser:return HttpResponseForbidden('Only a super administrator can change platform-wide settings.')
    config=SiteConfiguration.objects.filter(pk=1).first() or SiteConfiguration(pk=1)
    form=SiteConfigurationForm(request.POST or None,instance=config)
    if request.method=='POST' and form.is_valid():item=form.save();audit(request,'settings.updated',item,fields=form.changed_data);messages.success(request,text('Changes saved.'));return redirect('management_dashboard')
    return render(request,'management/edit.html',{'form':form,'management_title':'Site settings'})

@administrator
def school_media(request,pk):
    profile=get_object_or_404(scoped_records(request,'schools'),pk=pk)
    form=SchoolMediaForm(request.POST or None,request.FILES or None)
    if request.method=='POST' and form.is_valid():
        image=form.save(commit=False);image.school_profile=profile;image.uploaded_by=request.user;image.save();audit(request,'school_media.added',image,school=profile.school);messages.success(request,text('Changes saved.'));return redirect('management_school_media',pk=pk)
    return render(request,'management/school_media.html',{'form':form,'school_profile':profile,'photos':profile.media.all()})

@administrator
@require_POST
def school_media_delete(request,pk):
    image=get_object_or_404(SchoolMedia,pk=pk);get_object_or_404(scoped_records(request,'schools'),pk=image.school_profile_id);profile=image.school_profile_id;audit(request,'school_media.deleted',image,school=image.school_profile.school);image.delete();return redirect('management_school_media',pk=profile)

@login_required
def private_child_photo(request,pk):
    from django.http import FileResponse
    child=get_object_or_404(ChildProfile.objects.select_related('parent__user'),pk=pk)
    owns=child.parent.user_id==request.user.pk
    admin=moderator(request.user) and scoped_records(request,'children').filter(pk=child.pk).exists()
    if not (owns or admin) or not child.photo:raise Http404()
    response=FileResponse(child.photo.open('rb'),content_type='image/jpeg');response['Cache-Control']='private, no-store';response['X-Content-Type-Options']='nosniff';return response

def public_school_photo(request,pk):
    from django.http import FileResponse
    image=get_object_or_404(SchoolMedia,pk=pk,school_profile__is_published=True,permission_confirmed=True)
    if image.includes_children and not image.guardian_consent:raise Http404()
    response=FileResponse(image.image.open('rb'),content_type='image/jpeg');response['Cache-Control']='private, no-store' if image.includes_children else 'public, max-age=300';response['X-Content-Type-Options']='nosniff';return response

@administrator
def research_queue(request):
    targets=json.loads((settings.BASE_DIR/'content/research-targets.json').read_text())
    if request.method=='POST':
        if not request.user.is_superuser:return HttpResponseForbidden('Only a super administrator can add other schools to the directory.')
        target=next((row for row in targets['schools'] if row['key']==request.POST.get('key')),None)
        if not target:raise Http404()
        matches=list(SchoolProfile.objects.filter(name__iexact=target['name'])[:2])
        if len(matches)>1:messages.error(request,'Multiple matching profiles exist. Review existing records before continuing.');return redirect('management_research')
        item=matches[0] if matches else SchoolProfile.objects.create(name=target['name'],slug='research-'+target['key'],city='',website=target['url'],source_url=target['url'],source_name='User-provided research target; website not yet checked',is_published=False)
        if not matches:audit(request,'research.draft_created',item,fields=['name','website','is_published'])
        return redirect('management_edit',kind='schools',pk=item.pk)
    return render(request,'management/research.html',{'targets':targets})

@administrator
def family_detail(request,pk):
    family=get_object_or_404(scoped_records(request,'families'),pk=pk)
    return render(request,'management/family_detail.html',{'managed_family':family,'managed_children':family.children.all()})

@administrator
def family_child_new(request,pk):
    family=get_object_or_404(scoped_records(request,'families'),pk=pk)
    child=ChildProfile(parent=family);form=PrivateChildForm(request.POST or None,request.FILES or None,instance=child)
    if request.method=='POST' and form.is_valid():
        if family.children.filter(nickname__iexact=form.cleaned_data['nickname']).exists():form.add_error('nickname','A matching child profile already exists in this family. Edit it instead of creating a duplicate.')
        else:
            item=form.save();audit(request,'child.created',item,fields=form.changed_data);messages.success(request,text('Changes saved.'));return redirect('management_family_detail',pk=pk)
    return render(request,'management/edit.html',{'form':form,'management_title':'Child profile'})

@administrator
def review(request,kind,pk):
    from .management_forms import OrganizerReviewForm,ReportReviewForm
    if kind not in ['reports','organisers']:raise Http404()
    item=get_object_or_404(scoped_records(request,kind),pk=pk)
    form=ReportReviewForm(request.POST or None,instance=item) if kind=='reports' else OrganizerReviewForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        if kind=='reports':
            item=form.save(commit=False);item.reviewed_by=request.user;item.reviewed_at=timezone.now();item.save();audit(request,'report.reviewed',item,school=item.school,fields=form.changed_data)
        else:
            from .organizers import review_application
            try:item=review_application(request.user,request.member,item.pk,form.cleaned_data['status'],form.cleaned_data['note'])
            except (ValueError,PermissionError) as error:form.add_error(None,str(error))
            else:audit(request,'organizer.reviewed',item,school=item.school,fields=['status','decision_note'])
        if not form.errors:messages.success(request,text('Review saved.'));return redirect('management_records',kind=kind)
    return render(request,'management/review.html',{'form':form,'review_kind':kind,'review_record':item})
