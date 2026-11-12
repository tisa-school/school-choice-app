"""Family seats, moderated experiences and permission-controlled team photographs."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction,IntegrityError
from django.db.models import Q
from django.http import Http404,FileResponse,HttpResponseForbidden
from django.shortcuts import render,redirect,get_object_or_404
from django.views.decorators.http import require_POST
from .models import Event,FamilyBooking,EventExperience,ExperiencePhoto,ExperienceReport,TeamPhoto,ParentAccount,School
from .discovery import discovery_view,visible_events,membership
from .organizers import can_manage
from .attendance import book_family,decide_booking
from .community_forms import ExperienceForm,TeamPhotoForm,PhotoCaptionForm,ReportExperienceForm,UPLOAD_NOTICE
from .forms import FamilyBookingForm
from .localization import text


def moderator(user,school_id=None):
    member=membership(user)
    return bool(user.is_authenticated and (user.is_superuser or (member and member.verified and member.role=='staff' and (school_id is None or member.school_id==school_id))))


def can_contribute(user):
    member=membership(user)
    return bool(user.is_authenticated and (user.is_superuser or ParentAccount.objects.filter(user=user).exists() or (member and member.verified and member.role in ['staff','organizer'])))


def experiences_for(user,event):
    qs=event.experiences.select_related('author').prefetch_related('photos')
    if moderator(user,event.school_id): return qs.order_by('-created_at')
    return qs.filter(Q(status='published')|Q(author=user) if user.is_authenticated else Q(status='published')).order_by('-created_at')


@login_required
@discovery_view
def family_registration(request,pk):
    event=get_object_or_404(visible_events(request.user),pk=pk)
    if not ParentAccount.objects.filter(user=request.user).exists():return redirect('parent_setup')
    session=None
    session_id=request.POST.get('session') or request.GET.get('session')
    if event.listing_type=='activity':session=get_object_or_404(event.sessions,pk=int(session_id) if str(session_id).isdigit() else 0,is_cancelled=False)
    form=FamilyBookingForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        try:
            book_family(request.user,event.pk,form.cleaned_data['adults'],form.cleaned_data['children'],session.pk if session else None)
            messages.success(request,text('Registration sent. Spaces are allocated only after organizer confirmation.'))
            return redirect('family')
        except (ValueError,IntegrityError) as error:form.add_error(None,text(str(error) if isinstance(error,ValueError) else 'An active family registration already exists.'))
    return render(request,'community/group_registration.html',{'form':form,'event':event,'session':session,'target':session or event})


@login_required
@require_POST
def booking_action(request,pk,action):
    item=get_object_or_404(FamilyBooking,pk=pk)
    try:decide_booking(request.user,item.pk,action)
    except PermissionError:raise Http404()
    except ValueError as error:messages.error(request,text(str(error)))
    else:messages.success(request,text('Family registration updated.'))
    return redirect('organizer_event',pk=item.event_id) if can_manage(request.user,membership(request.user),item.event) else redirect('family')


@login_required
@discovery_view
def experience_edit(request,event_id,pk=None):
    event=get_object_or_404(visible_events(request.user),pk=event_id)
    if not can_contribute(request.user):return HttpResponseForbidden(text('Parents, guardians and authorized organizers can share experiences.'))
    with transaction.atomic():
        item=get_object_or_404(EventExperience.objects.select_for_update(),pk=pk,event=event,author=request.user) if pk else EventExperience(event=event,author=request.user)
        form=ExperienceForm(request.POST or None,request.FILES or None,instance=item)
        if request.method=='POST' and form.is_valid():
            item=form.save(False);item.status='pending';item.reviewed_by=None;item.save()
            for image in form.cleaned_data['photos']:ExperiencePhoto.objects.create(experience=item,image=image,description=form.cleaned_data['photo_description'])
            messages.success(request,text('Your contribution was saved and is awaiting moderation.'))
            return redirect('detail',pk=event.pk)
    return render(request,'community/experience_form.html',{'form':form,'event':event,'experience':item})


@login_required
@require_POST
def experience_delete(request,pk):
    item=get_object_or_404(EventExperience,pk=pk,author=request.user)
    event_id=item.event_id;item.delete();messages.success(request,text('Contribution deleted.'))
    return redirect('detail',pk=event_id)


@login_required
@discovery_view
def experience_photo_edit(request,pk):
    photo=get_object_or_404(ExperiencePhoto,pk=pk,experience__author=request.user)
    form=PhotoCaptionForm(request.POST or None,instance=photo)
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            form.save();EventExperience.objects.filter(pk=photo.experience_id).update(status='pending',reviewed_by=None)
        messages.success(request,text('Your contribution was saved and is awaiting moderation.'));return redirect('detail',pk=photo.experience.event_id)
    return render(request,'community/form.html',{'form':form,'title':text('Edit photo description'),'submit':text('Save photo')})


@login_required
@require_POST
def experience_photo_delete(request,pk):
    photo=get_object_or_404(ExperiencePhoto,pk=pk,experience__author=request.user)
    event_id=photo.experience.event_id;photo.delete();messages.success(request,text('Photo deleted.'))
    return redirect('detail',pk=event_id)


@login_required
@discovery_view
def report_experience(request,pk,photo_id=None):
    item=get_object_or_404(EventExperience,pk=pk,event__in=visible_events(request.user),status='published')
    photo=get_object_or_404(item.photos,pk=photo_id,hidden=False) if photo_id else None
    form=ReportExperienceForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        ExperienceReport.objects.get_or_create(experience=item,reported_by=request.user,resolved=False,defaults={'reason':form.cleaned_data['reason'],'photo':photo})
        messages.success(request,text('Report sent to administrators.'));return redirect('detail',pk=item.event_id)
    return render(request,'community/form.html',{'form':form,'title':text('Report inappropriate content'),'submit':text('Send report')})


@login_required
@discovery_view
def moderation(request):
    if not moderator(request.user):raise Http404()
    pending=EventExperience.objects.filter(status='pending').select_related('event','author').prefetch_related('photos')
    reports=ExperienceReport.objects.filter(resolved=False).select_related('experience__event','photo')
    if not request.user.is_superuser:
        pending=pending.filter(event__school=request.member.school);reports=reports.filter(experience__event__school=request.member.school)
    return render(request,'community/moderation.html',{'pending':pending,'reports':reports})


@login_required
@require_POST
def moderate_experience(request,pk,action):
    with transaction.atomic():
        item=get_object_or_404(EventExperience.objects.select_for_update(),pk=pk)
        if not moderator(request.user,item.event.school_id):raise Http404()
        if action not in ['publish','hide','resolve']:raise Http404()
        if action!='resolve':item.status='published' if action=='publish' else 'hidden';item.reviewed_by=request.user;item.save()
        item.reports.filter(resolved=False).update(resolved=True)
    messages.success(request,text('Moderation decision saved.'));return redirect('content_moderation')


@login_required
@require_POST
def moderate_photo(request,pk):
    photo=get_object_or_404(ExperiencePhoto,pk=pk)
    if not moderator(request.user,photo.experience.event.school_id):raise Http404()
    photo.hidden=True;photo.save(update_fields=['hidden']);messages.success(request,text('Photo hidden.'));return redirect('content_moderation')


def team_visible(user):
    member=membership(user)
    permitted=Q(visibility='public',sharing_permission=True)&(Q(is_student=False,includes_children=False)|Q(guardian_consent=True))
    if member:
        permitted|=Q(school=member.school,visibility='school',sharing_permission=True)&(Q(is_student=False,includes_children=False)|Q(guardian_consent=True))
        if moderator(user,member.school_id):permitted|=Q(school=member.school)
    if user.is_authenticated and user.is_superuser:return TeamPhoto.objects.all()
    return TeamPhoto.objects.filter(permitted)


@discovery_view
def team_gallery(request):
    photos=team_visible(request.user).select_related('school')
    if request.GET.get('kind')=='group':photos=photos.filter(is_group=True)
    elif request.GET.get('kind')=='individual':photos=photos.filter(is_group=False)
    elif request.GET.get('kind')=='students':photos=photos.filter(is_student=True)
    photos=list(photos)
    for photo in photos:photo.can_manage=moderator(request.user,photo.school_id)
    return render(request,'community/team_gallery.html',{'photos':photos,'can_upload':moderator(request.user)})


@login_required
@discovery_view
def team_photo_edit(request,pk=None):
    if not moderator(request.user):raise Http404()
    photo=get_object_or_404(TeamPhoto,pk=pk) if pk else TeamPhoto(uploaded_by=request.user)
    if pk and not moderator(request.user,photo.school_id):raise Http404()
    import json
    from django.conf import settings
    roster=json.loads((settings.BASE_DIR/'content/project.json').read_text())['contributors']
    selected=next((person for person in roster if person['id']==request.GET.get('person')),None)
    initial={'name':selected['public_name'],'role':selected['role'],'is_student':selected['group']=='students','visibility':'private'} if selected and not pk else {}
    form=TeamPhotoForm(request.POST or None,request.FILES or None,instance=photo,initial=initial)
    if not request.user.is_superuser:form.fields['school'].queryset=School.objects.filter(pk=request.member.school_id);form.initial['school']=request.member.school_id
    if request.method=='POST' and form.is_valid():form.save();messages.success(request,text('Team photo saved.'));return redirect('team_gallery')
    return render(request,'community/team_photo_form.html',{'form':form,'upload_notice':UPLOAD_NOTICE,'photo':photo,'roster':roster})


@login_required
@require_POST
def team_photo_delete(request,pk):
    photo=get_object_or_404(TeamPhoto,pk=pk)
    if not moderator(request.user,photo.school_id):raise Http404()
    photo.delete();messages.success(request,text('Photo deleted.'));return redirect('team_gallery')


@discovery_view
def protected_photo(request,kind,pk):
    if kind=='team':photo=get_object_or_404(team_visible(request.user),pk=pk)
    elif kind=='experience':
        photo=get_object_or_404(ExperiencePhoto.objects.select_related('experience__event'),pk=pk)
        item=photo.experience
        privileged=moderator(request.user,item.event.school_id) or (request.user.is_authenticated and request.user.pk==item.author_id)
        if not privileged and (not visible_events(request.user).filter(pk=item.event_id).exists() or item.status!='published' or photo.hidden):raise Http404()
    else:raise Http404()
    response=FileResponse(photo.image.open('rb'),content_type='image/jpeg')
    response['Cache-Control']='private, no-store';response['X-Content-Type-Options']='nosniff';response['Content-Disposition']='inline; filename="photo.jpg"'
    return response


def interface_language(request):
    from django.http import JsonResponse
    from .localization import catalog,ACTIVE_LOCALES
    code=getattr(request,'ui_locale','en')
    return JsonResponse({'language':code,'dictionary':catalog(code),'direction':'rtl' if code in ['ar','ur'] else 'ltr','intl_locale':ACTIVE_LOCALES[code][2]})


def photo_save_errors(view):
    from functools import wraps
    @wraps(view)
    def wrapped(request,*args,**kwargs):
        from django.db import DatabaseError
        try:return view(request,*args,**kwargs)
        except (DatabaseError,OSError):
            import logging
            from django.http import JsonResponse
            logging.getLogger(__name__).exception('Private portrait save failed')
            message=text('Photo could not be saved. Please try again or contact an administrator.')
            if request.headers.get('X-Requested-With')=='XMLHttpRequest':return JsonResponse({'error':message},status=503)
            messages.error(request,message);return redirect('/about/#our-team')
    return wrapped


@login_required
@require_POST
@photo_save_errors
def team_inline_upload(request,person_id):
    import json
    from django.conf import settings
    from django.http import JsonResponse
    from .community_forms import PortraitCropForm
    project=json.loads((settings.BASE_DIR/'content/project.json').read_text())
    person=next((p for p in project['contributors'] if p['id']==person_id),None)
    from .team import person_names
    if not person or not moderator(request.user):raise Http404()
    member=membership(request.user)
    from .team import project_school
    school=project_school(project)
    if school is None or not moderator(request.user,school.pk):raise Http404()
    ajax=request.headers.get('X-Requested-With')=='XMLHttpRequest'
    if request.POST.get('action')=='delete':
        with transaction.atomic():
            School.objects.select_for_update().get(pk=school.pk)
            TeamPhoto.objects.filter(school=school,name__in=person_names(person),is_group=False).delete()
        from .models import PlatformAudit
        PlatformAudit.objects.create(actor=request.user,school=school,action='portrait.deleted',entity_type='TeamProfile',entity_id=person_id,changed_fields=['image'])
        message=text('Photo deleted.')
        if ajax:return JsonResponse({'message':message,'deleted':True})
        messages.success(request,message)
        return redirect('/about/#our-team')
    form=PortraitCropForm(request.POST,request.FILES)
    if not form.is_valid():
        errors=' '.join(text(str(error)) for values in form.errors.values() for error in values)
        if ajax:return JsonResponse({'error':errors},status=400)
        messages.error(request,errors)
        return redirect('/about/#our-team')
    with transaction.atomic():
        # A school row lock serializes replacements, including the first upload.
        School.objects.select_for_update().get(pk=school.pk)
        photos=TeamPhoto.objects.filter(school=school,name__in=person_names(person),is_group=False).order_by('-created_at','-pk')
        photo=photos.first() or TeamPhoto(school=school)
        photo.name=person['public_name'];photo.role=person['role']
        photo.is_student=person['group']=='students';photo.includes_children=photo.is_student
        photo.uploaded_by=request.user;photo.image=form.cleaned_data['image']
        photo.description=person['public_name'].split()[0] if photo.is_student else person['public_name']
        photo.visibility='private';photo.sharing_permission=False;photo.guardian_consent=False
        photo.save()
        # Older portraits must not remain publicly visible after a private replacement.
        photos.exclude(pk=photo.pk).update(visibility='private',sharing_permission=False,guardian_consent=False)
    from .management_views import audit
    audit(request,'portrait.updated',photo,school=school,fields=['image','visibility'])
    message=text('Team photo saved.')
    if ajax:
        from django.urls import reverse
        return JsonResponse({'message':message,'url':reverse('protected_photo',args=['team',photo.pk]),'description':photo.description})
    messages.success(request,message)
    return redirect('/about/#our-team')
