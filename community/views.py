import calendar
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from functools import wraps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction, IntegrityError
from django.db.models import Q, Count
from django.http import Http404, FileResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import *
from .forms import *
from .services import request_ticket, decide, cancel, publish_due, notify_school
from .discovery import discovery_view, visible_events, filter_listings, LANGUAGES, membership
from .services import express_interest, parent_decision, confirm_participation
from .persistence import saved_success

def post_id(request,name):
    value=request.POST.get(name,'')
    return int(value) if value.isdigit() and len(value)<12 else 0

def scoped(staff=False):
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapped(request,*args,**kwargs):
            member=Membership.objects.select_related('school').filter(user=request.user).first()
            if not member: return redirect('join')
            if staff and not(member.role=='staff' and member.verified): return HttpResponseForbidden('Verified school staff access is required.')
            request.member=member
            timezone.activate(ZoneInfo(member.school.time_zone))
            publish_due(member.school)
            return view(request,*args,**kwargs)
        return wrapped
    return decorator

def welcome(request):
    if request.user.is_authenticated: return redirect('home')
    return render(request,'community/welcome.html')
def signup(request):
    if request.user.is_authenticated: return redirect('home')
    form=SignupForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        email=form.cleaned_data['email'].lower()
        if not User.objects.filter(username=email).exists():
            try:
                with transaction.atomic(): user=form.save()
            except IntegrityError: user=None
            if user:
                login(request,user);return redirect('parent_setup' if request.GET.get('family')=='1' else 'join')
        # Deliberately avoid an account-existence oracle.
        messages.info(request,'If registration can be completed, you can continue. Otherwise try logging in or recovering your password.')
        return redirect('login')
    return render(request,'community/form.html',{'form':form,'title':'Your school life, connected.','eyebrow':'JOIN TK-ZONE','submit':'Create account ✦','auth':True})
@login_required
def join(request):
    if Membership.objects.filter(user=request.user).exists(): return redirect('home')
    form=JoinForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        school=form.cleaned_data['school']
        if school.valid_invite(form.cleaned_data['code']):
            Membership.objects.create(user=request.user,school=school,role='parent' if ParentAccount.objects.filter(user=request.user).exists() else 'student',verified=True)
            saved_success(request,'School membership saved ✦')
            return redirect('home')
        form.add_error('code','The school and invite code could not be verified. Ask your school for a current code.')
    return render(request,'community/form.html',{'form':form,'title':'Find your people.','eyebrow':'YOUR SCHOOL','submit':'Join school ✦','help':'Choose your school and use the private invite code supplied by your school. Staff access is granted separately by a trusted administrator.','school_search':True})

def public_events(request):
    return visible_events(request.user)

@discovery_view
def home(request):
    from .models import FamilyPlan
    listings=public_events(request)
    events=listings.filter(listing_type='event',start_at__gte=timezone.now())
    activities=listings.filter(listing_type='activity').filter(Q(sessions__start_at__gte=timezone.now(),sessions__is_cancelled=False)|Q(sessions__isnull=True)).distinct()
    is_activities=request.path=='/activities/'
    explorer=request.path in ['/events/','/activities/']
    queryset=activities if is_activities else events
    filtered=filter_listings(queryset,request.GET).order_by('start_at')
    saved_ids=set(SavedEvent.objects.filter(user=request.user).values_list('event_id',flat=True)) if request.user.is_authenticated else set()
    notes=Announcement.objects.filter(school=request.member.school,status='published').order_by('-is_pinned','-published_at')[:2] if request.member else []
    return render(request,'community/discover.html',{'events':filtered,'activities':filter_listings(activities,request.GET).order_by('start_at')[:6] if not explorer else [],'categories':['All']+list(dict(CATEGORIES)),'q':request.GET.get('q',''),'category':request.GET.get('category','All'),'filters':request.GET,'languages':LANGUAGES,'saved_ids':saved_ids,'announcements':notes,'explorer':explorer,'is_activities':is_activities,'family_plans':FamilyPlan.objects.filter(parent__user=request.user,event__in=public_events(request)).select_related('event','session')[:3] if request.user.is_authenticated else []})

@discovery_view
def detail(request,pk):
    event=get_object_or_404(public_events(request),pk=pk)
    timezone.activate(ZoneInfo(event.time_zone))
    authenticated=request.user.is_authenticated
    parent=ParentAccount.objects.filter(user=request.user).first() if authenticated else None
    return render(request,'community/listing_detail.html',{'event':event,'saved':SavedEvent.objects.filter(user=request.user,event=event).exists() if authenticated else False,'ticket':TicketRequest.objects.filter(student=request.user,event=event).order_by('-created_at').first() if authenticated else None,'collections':Collection.objects.filter(user=request.user) if authenticated else [],'children':parent.children.all() if parent else [],'sessions':event.sessions.filter(start_at__gt=timezone.now()).order_by('start_at')})
@scoped()
@require_POST
def ticket_request(request,pk):
    get_object_or_404(public_events(request),pk=pk,school=request.member.school,listing_type='event')
    try: request_ticket(request.user,request.member,pk);saved_success(request,'✦ Request sent. Your ticket is awaiting staff approval.')
    except ValueError as e: messages.error(request,str(e))
    return redirect('tickets')
@scoped()
def tickets(request):
    return render(request,'community/tickets.html',{'tickets':TicketRequest.objects.filter(student=request.user,event__school=request.member.school).select_related('event').order_by('-created_at')})
@scoped()
@require_POST
def cancel_ticket(request,pk):
    get_object_or_404(TicketRequest,pk=pk,student=request.user,event__school=request.member.school)
    try: cancel(request.user,request.member,pk);saved_success(request,'Ticket cancelled. Your spot has been released.')
    except ValueError as e: messages.error(request,str(e))
    return redirect('tickets')
@login_required
@discovery_view
@require_POST
def save_event(request,pk):
    event=get_object_or_404(public_events(request),pk=pk)
    with transaction.atomic():
        saved=SavedEvent.objects.filter(user=request.user,event=event).first()
        if saved:
            saved.delete()
            for collection in Collection.objects.filter(user=request.user): collection.events.remove(event)
            saved_success(request,'Event removed from saved.')
        else: SavedEvent.objects.create(user=request.user,event=event);saved_success(request,'✦ Saved for later.')
    return redirect('detail',pk=pk)
@login_required
@discovery_view
def saved(request):
    events=public_events(request).filter(savedevent__user=request.user).order_by('start_at')
    collection=None
    if request.GET.get('collection'):
        collection=get_object_or_404(Collection,pk=request.GET['collection'],user=request.user)
        events=events.filter(collection=collection)
    return render(request,'community/saved.html',{'events':events,'collections':Collection.objects.filter(user=request.user),'collection':collection,'saved_ids':set(events.values_list('id',flat=True))})
@login_required
@discovery_view
def collection_edit(request,pk=None):
    collection=get_object_or_404(Collection,pk=pk,user=request.user) if pk else Collection(user=request.user)
    form=CollectionForm(request.POST or None,instance=collection)
    if request.method=='POST' and form.is_valid(): form.save();saved_success(request,'Collection saved ✦');return redirect('saved')
    return render(request,'community/form.html',{'form':form,'title':'Your own little constellation.','submit':'Save collection ✦','eyebrow':'SAVED COLLECTIONS'})
@login_required
@discovery_view
@require_POST
def collection_action(request,pk):
    collection=get_object_or_404(Collection,pk=pk,user=request.user)
    if request.POST.get('action')=='delete': collection.delete();saved_success(request,'Collection deleted. Your saved events are still here.')
    else:
        event=get_object_or_404(public_events(request),pk=request.POST.get('event'))
        if not SavedEvent.objects.filter(user=request.user,event=event).exists(): messages.error(request,'Save the event before adding it to a collection.')
        elif request.POST.get('action')=='remove': collection.events.remove(event);saved_success(request,'Removed from collection.')
        else: collection.events.add(event);saved_success(request,'Added to collection ✦')
    return redirect('saved')
@scoped()
def announcements(request):
    return render(request,'community/announcements.html',{'announcements':Announcement.objects.filter(school=request.member.school,status='published').order_by('-is_pinned','-published_at')})
@login_required
@discovery_view
def notifications(request):
    return render(request,'community/notifications.html',{'notifications':Notification.objects.filter(user=request.user).order_by('-created_at')})
@login_required
@discovery_view
@require_POST
def read_notification(request,pk):
    item=get_object_or_404(Notification,pk=pk,user=request.user)
    item.is_read=True;item.save(update_fields=['is_read']);saved_success(request,'Notification marked as read')
    return redirect(item.link if item.link.startswith(('/events/','/tickets/','/announcements/','/staff/requests/','/family/')) else 'notifications')
@login_required
@discovery_view
def profile(request):
    form=ProfileForm(request.POST or None,instance=request.user)
    if request.method=='POST' and form.is_valid(): form.save();saved_success(request,'Profile updated ✦');return redirect('profile')
    return render(request,'community/profile.html',{'form':form})
@scoped(staff=True)
def staff_home(request):
    school=request.member.school
    return render(request,'community/staff.html',{'events':Event.objects.filter(school=school).order_by('-created_at'),'event_count':Event.objects.filter(school=school,status='published').count(),'pending_count':TicketRequest.objects.filter(event__school=school,status__in=['requested','under_review']).count()+Participation.objects.filter(event__school=school,status='organizer_pending').count(),'approved_count':TicketRequest.objects.filter(event__school=school,status='approved').count()+Participation.objects.filter(event__school=school,status='confirmed').count(),'announcement_count':Announcement.objects.filter(school=school,status='published').count()})
@scoped(staff=True)
def event_edit(request,pk=None):
    with transaction.atomic():
        event=get_object_or_404(Event.objects.select_for_update(),pk=pk,school=request.member.school) if pk else Event(school=request.member.school,created_by=request.user)
        timezone.activate(ZoneInfo(event.time_zone))
        was_published=event.status=='published'
        form=EventForm(request.POST or None,request.FILES or None,instance=event)
        if request.method=='POST' and form.is_valid():
            event=form.save(False)
            if event.status=='published':
                event.published_at=timezone.now()
                event.published_by=request.user
            event.save()
            if was_published:
                users=User.objects.filter(Q(ticketrequest__event=event)|Q(savedevent__event=event)|Q(parentaccount__children__participations__event=event)).distinct()
                Notification.objects.bulk_create([Notification(user=u,school=event.school,kind='event',title='Event updated',message='A listing you saved or requested has changed. Check its latest details if it is still available.',link=f'/events/{event.pk}/' if event.status=='published' else '/family/' if ParentAccount.objects.filter(user=u).exists() else '/tickets/') for u in users])
            saved_success(request,'Event saved ✦');return redirect('staff')
    return render(request,'community/event_form.html',{'form':form,'title':'Make something memorable.','eyebrow':'EVENT STUDIO','event':event})
@scoped(staff=True)
def approval_center(request):
    requests=TicketRequest.objects.filter(event__school=request.member.school).select_related('event','student').order_by('created_at')
    status=request.GET.get('status','pending')
    if status=='pending': requests=requests.filter(status__in=['requested','under_review'])
    elif status in dict(TicketRequest.STATUSES): requests=requests.filter(status=status)
    if request.GET.get('event','').isdigit(): requests=requests.filter(event_id=request.GET['event'])
    return render(request,'community/approvals.html',{'family_requests':Participation.objects.filter(event__school=request.member.school,status='organizer_pending').select_related('event','session','child').order_by('created_at'),'requests':requests,'status':status,'statuses':TicketRequest.STATUSES,'events':Event.objects.filter(school=request.member.school),'selected_event':request.GET.get('event','')})
@scoped(staff=True)
@require_POST
def decision(request,pk):
    get_object_or_404(TicketRequest,pk=pk,event__school=request.member.school)
    try: decide(request.user,request.member,pk,request.POST.get('status'),request.POST.get('note',''));saved_success(request,'Decision saved and student notified ✦')
    except ValueError as e: messages.error(request,str(e))
    return redirect('approvals')
@scoped(staff=True)
def studio(request):
    return render(request,'community/studio.html',{'announcements':Announcement.objects.filter(school=request.member.school).order_by('-created_at')})
@scoped(staff=True)
def announcement_edit(request,pk=None):
    with transaction.atomic():
        item=get_object_or_404(Announcement.objects.select_for_update(),pk=pk,school=request.member.school) if pk else Announcement(school=request.member.school,author=request.user)
        old_status=item.status
        form=AnnouncementForm(request.POST or None,request.FILES or None,instance=item)
        if request.method=='POST' and form.is_valid():
            item=form.save(False)
            if item.status=='published' and old_status!='published': item.published_at=timezone.now()
            item.save()
            if item.status=='published' and old_status!='published': notify_school(item)
            saved_success(request,'Announcement saved ✦');return redirect('studio')
    return render(request,'community/announcement_form.html',{'form':form,'title':'A little news. A closer school.','eyebrow':'ANNOUNCEMENT STUDIO'})
@discovery_view
def media(request,kind,pk):
    model=Event if kind=='event' else Announcement if kind=='announcement' else None
    if model is None: raise Http404()
    if model is Event:
        obj=public_events(request).filter(pk=pk).first()
        if obj is None and request.member:
            privileged=(request.member.role=='staff' and request.member.verified)
            owned=(request.member.role=='organizer' and request.member.verified)
            query=Event.objects.filter(pk=pk,school=request.member.school)
            if privileged: obj=query.first()
            elif owned: obj=query.filter(created_by=request.user).first()
        if obj is None: raise Http404()
    else:
        if not request.member: raise Http404()
        obj=get_object_or_404(Announcement,pk=pk,school=request.member.school)
        if obj.status!='published' and not(request.member.role=='staff' and request.member.verified): raise Http404()
    if not obj.image: raise Http404()
    response=FileResponse(obj.image.open('rb'))
    response['Cache-Control']='private, no-store'
    response['X-Content-Type-Options']='nosniff'
    return response


@login_required
@discovery_view
def parent_setup(request):
    if ParentAccount.objects.filter(user=request.user).exists(): return redirect('family')
    if request.member and request.member.role=='student': return HttpResponseForbidden('A school student account cannot become a parent account. A guardian should register their own account.')
    form=ParentSetupForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        ParentAccount.objects.get_or_create(user=request.user)
        saved_success(request,'Family workspace saved ✦')
        return redirect('family')
    return render(request,'community/form.html',{'form':form,'title':'A little more family time.','eyebrow':'PARENT ACCOUNT','submit':'Create my family workspace ✦','help':'An adult parent or legal guardian manages this private workspace. No child profiles are public. This declaration is not an identity-verification badge.'})

def parent_required(view):
    @login_required
    @discovery_view
    @wraps(view)
    def wrapped(request,*args,**kwargs):
        request.parent=ParentAccount.objects.filter(user=request.user).first()
        if not request.parent: return redirect('parent_setup')
        return view(request,*args,**kwargs)
    return wrapped

@parent_required
def family(request):
    items=Participation.objects.filter(child__parent=request.parent).select_related('event','session','child').order_by('-created_at')
    plans=sorted(FamilyPlan.objects.filter(parent=request.parent).select_related('event','session'),key=lambda plan:(plan.session or plan.event).start_at)
    return render(request,'community/family.html',{'children':request.parent.children.all(),'participations':items,'plans':plans,'visible_ids':set(public_events(request).values_list('pk',flat=True))})

@parent_required
def child_edit(request,pk=None):
    child=get_object_or_404(ChildProfile,pk=pk,parent=request.parent) if pk else ChildProfile(parent=request.parent)
    form=ChildProfileForm(request.POST or None,instance=child)
    if request.method=='POST' and form.is_valid(): form.save();saved_success(request,'Private child profile saved ✦');return redirect('family')
    return render(request,'community/form.html',{'form':form,'title':'Their own little interests.','eyebrow':'PRIVATE FAMILY PROFILE','submit':'Save child profile ✦','help':'Use a nickname and age band. No exact birth date, school class, public photo, or live location is collected.'})

@parent_required
@require_POST
def child_delete(request,pk):
    get_object_or_404(ChildProfile,pk=pk,parent=request.parent).delete()
    saved_success(request,'Child profile and its participation records deleted.')
    return redirect('family')

@parent_required
@require_POST
def interest(request,pk):
    event=get_object_or_404(public_events(request),pk=pk)
    child=get_object_or_404(ChildProfile,pk=post_id(request,'child'),parent=request.parent)
    session_id=post_id(request,'session') or None
    if event.listing_type=='activity': get_object_or_404(ActivitySession,pk=session_id or 0,activity=event,is_cancelled=False)
    try: express_interest(request.user,pk,child.pk,session_id);saved_success(request,'Interest saved. Send it for parent review in your family workspace ✦')
    except ValueError as e: messages.error(request,str(e))
    return redirect('family')

@parent_required
@require_POST
def parent_review(request,pk):
    get_object_or_404(Participation,pk=pk,child__parent=request.parent)
    try: parent_decision(request.user,pk,request.POST.get('action'),request.POST.get('password',''));saved_success(request,'Family request updated ✦')
    except ValueError as e: messages.error(request,str(e))
    return redirect('family')

@parent_required
@require_POST
def plan_add(request,pk):
    event=get_object_or_404(public_events(request),pk=pk)
    session=None
    if event.listing_type=='activity': session=get_object_or_404(ActivitySession,pk=post_id(request,'session'),activity=event,is_cancelled=False)
    FamilyPlan.objects.get_or_create(parent=request.parent,event=event,session=session,defaults={'note':request.POST.get('note','')[:200]})
    saved_success(request,'Added to your family plan. This does not reserve a place ✦')
    return redirect('family')

@parent_required
@require_POST
def plan_delete(request,pk):
    get_object_or_404(FamilyPlan,pk=pk,parent=request.parent).delete()
    saved_success(request,'Family plan updated ✦')
    return redirect('family')

@parent_required
def family_calendar(request):
    from django.http import HttpResponse
    def escape(value): return str(value).replace('\\','\\\\').replace(';','\\;').replace(',','\\,').replace('\n','\\n').replace('\r','')
    rows=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//TK-ZONE//Family Calendar//EN']
    for plan in FamilyPlan.objects.filter(parent=request.parent,event__in=public_events(request)).select_related('event','session'):
        target=plan.session or plan.event
        if plan.session and plan.session.is_cancelled: continue
        rows+=['BEGIN:VEVENT','UID:plan-'+str(plan.pk)+'@tk-zone','DTSTAMP:'+timezone.now().strftime('%Y%m%dT%H%M%SZ'),'DTSTART:'+target.start_at.astimezone(ZoneInfo('UTC')).strftime('%Y%m%dT%H%M%SZ'),'SUMMARY:'+escape(plan.event.title+' (family plan — not a booking)'),'DESCRIPTION:'+escape(plan.note or 'A saved family plan; participation is not confirmed.'),'END:VEVENT']
    rows+=['END:VCALENDAR']
    response=HttpResponse('\r\n'.join(rows)+'\r\n',content_type='text/calendar; charset=utf-8');response['Content-Disposition']='attachment; filename="tkzone-family.ics"';response['Cache-Control']='private, no-store'
    return response

@scoped(staff=True)
@require_POST
def family_confirmation(request,pk):
    get_object_or_404(Participation,pk=pk,event__school=request.member.school)
    try: confirm_participation(request.user,request.member,pk,request.POST.get('status'),request.POST.get('note',''));saved_success(request,'Organizer decision saved and family notified ✦')
    except ValueError as e: messages.error(request,str(e))
    return redirect('approvals')

@scoped(staff=True)
def session_edit(request,event_id,pk=None):
    with transaction.atomic():
        event=get_object_or_404(Event.objects.select_for_update(),pk=event_id,school=request.member.school,listing_type='activity')
        timezone.activate(ZoneInfo(event.time_zone))
        session=get_object_or_404(ActivitySession.objects.select_for_update(),pk=pk,activity=event) if pk else ActivitySession(activity=event)
        form=SessionForm(request.POST or None,instance=session)
        if request.method=='POST' and form.is_valid():
            item=form.save()
            if item.is_cancelled:
                for participation in item.participations.exclude(status__in=['cancelled','declined']):
                    from .services import record_participation,participation_notice
                    previous=participation.status;participation.status='cancelled';participation.save();record_participation(participation,previous,request.user);participation_notice(participation,'Session cancelled','The organizer cancelled this session. No other session is reserved automatically.')
            else:
                from .services import participation_notice
                for participation in item.participations.exclude(status__in=['cancelled','declined']): participation_notice(participation,'Activity session updated','Check your family workspace for the latest session details.')
            saved_success(request,'Activity session saved ✦');return redirect('event_edit',pk=event.pk)
    return render(request,'community/form.html',{'form':form,'title':'One session. One little adventure.','eyebrow':event.title,'submit':'Save session ✦','help':'Each session has its own capacity and participation requests. Times use '+event.time_zone+'.'})

@login_required
@discovery_view
def organizer_workspace(request,pk=None):
    if not request.member or request.member.role!='organizer' or not request.member.verified: return HttpResponseForbidden('A trusted administrator must grant organizer access first.')
    event=get_object_or_404(Event,pk=pk,created_by=request.user,school=request.member.school) if pk else Event(school=request.member.school,created_by=request.user,visibility='public')
    form=OrganizerSubmissionForm(request.POST or None,request.FILES or None,instance=event)
    if request.method=='POST' and form.is_valid():
        item=form.save(False);item.status='submitted';item.published_by=None;item.identity_verified=False;item.save()
        from .services import staff_notify
        staff_notify(item.school,'Listing awaiting review','An organizer submitted a listing for publication review.','/staff/')
        saved_success(request,'Submitted for staff review. Nothing was published automatically ✦');return redirect('organizer')
    return render(request,'community/organizer.html',{'form':form,'listings':Event.objects.filter(created_by=request.user,school=request.member.school).order_by('-updated_at')})

@discovery_view
def finder(request):
    from .finder import interpret,recommendations,FinderUnavailable
    results=[];error='';preferences=request.POST.get('preferences','')[:500] if request.method=='POST' else '';accepted=request.POST.get('consent')=='on'
    if request.method=='POST':
        if not accepted: error='Confirm that your search contains preferences only, with no names or private information.'
        elif not preferences.strip(): error='Describe an activity you would like to find.'
        else:
            try: results=recommendations(request.user,interpret(preferences))
            except FinderUnavailable as e: error=str(e)
    return render(request,'community/finder.html',{'results':results,'error':error,'preferences':preferences,'searched':request.method=='POST' and not error,'ai_configured':bool(settings.AI_API_KEY)})
