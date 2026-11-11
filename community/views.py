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
from .attendance import confirmed_total

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
                login(request,user)
                from django.utils.http import url_has_allowed_host_and_scheme
                destination=request.GET.get('next','')
                if destination and url_has_allowed_host_and_scheme(destination,allowed_hosts={request.get_host()},require_https=request.is_secure()): return redirect(destination)
                return redirect('parent_setup' if request.GET.get('family')=='1' else 'join')
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
    if request.path=='/' and not request.user.is_authenticated:
        from .demo import presentation
        return presentation(request)
    from .models import FamilyPlan
    listings=public_events(request).filter(is_cancelled=False)
    events=listings.filter(listing_type='event',start_at__gte=timezone.now())
    activities=listings.filter(listing_type='activity').filter(Q(sessions__start_at__gte=timezone.now(),sessions__is_cancelled=False)|Q(sessions__isnull=True)).distinct()
    is_activities=request.path=='/activities/'
    explorer=request.path in ['/events/','/activities/']
    queryset=activities if is_activities else events
    filtered=filter_listings(queryset,request.GET).order_by('start_at')
    saved_ids=set(SavedEvent.objects.filter(user=request.user).values_list('event_id',flat=True)) if request.user.is_authenticated else set()
    notes=Announcement.objects.filter(school=request.member.school,status='published').order_by('-is_pinned','-published_at')[:2] if request.member and request.member.role!='organizer' else []
    return render(request,'community/discover.html',{'events':filtered,'activities':filter_listings(activities,request.GET).order_by('start_at')[:6] if not explorer else [],'categories':['All']+list(dict(CATEGORIES)),'q':request.GET.get('q',''),'category':request.GET.get('category','All'),'filters':request.GET,'languages':LANGUAGES,'saved_ids':saved_ids,'announcements':notes,'explorer':explorer,'is_activities':is_activities,'family_plans':FamilyPlan.objects.filter(parent__user=request.user,event__in=public_events(request)).select_related('event','session')[:3] if request.user.is_authenticated else []})

@discovery_view
def detail(request,pk):
    event=get_object_or_404(public_events(request),pk=pk)
    timezone.activate(ZoneInfo(event.time_zone))
    from urllib.parse import urlsplit
    back=request.GET.get('return_to','')
    try:
        parsed=urlsplit(back)
        if parsed.scheme or parsed.netloc or parsed.path not in ['/discover/activities/','/saved/']:back=''
    except ValueError:back=''
    request.discovery_return=back
    authenticated=request.user.is_authenticated
    parent=ParentAccount.objects.filter(user=request.user).first() if authenticated else None
    from .community_views import experiences_for,can_contribute
    return render(request,'community/listing_detail.html',{'experiences':experiences_for(request.user,event),'can_contribute':can_contribute(request.user),'discovery_return':getattr(request,'discovery_return',''),'duration_minutes':int((event.end_at-event.start_at).total_seconds()/60) if event.end_at and event.end_at>event.start_at else None,'event':event,'saved':SavedEvent.objects.filter(user=request.user,event=event).exists() if authenticated else False,'ticket':TicketRequest.objects.filter(student=request.user,event=event).order_by('-created_at').first() if authenticated else None,'collections':Collection.objects.filter(user=request.user) if authenticated else [],'children':parent.children.all() if parent else [],'sessions':event.sessions.filter(start_at__gt=timezone.now()).order_by('start_at')})
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
@discovery_view
def saved(request):
    from .family_discovery import saved_context
    if not request.user.is_authenticated:
        return render(request,'discovery/saved.html',saved_context(request))
    events=public_events(request).filter(savedevent__user=request.user).order_by('start_at')
    collection=None
    if request.GET.get('collection'):
        collection=get_object_or_404(Collection,pk=request.GET['collection'],user=request.user)
        events=events.filter(collection=collection)
    return render(request,'community/saved.html',{**saved_context(request),'events':events,'collections':Collection.objects.filter(user=request.user),'collection':collection,'saved_ids':set(events.values_list('id',flat=True))})
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
    if request.member.role=='organizer': return HttpResponseForbidden('School announcements are private to school families and staff.')
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
    return render(request,'community/staff.html',{'events':Event.objects.filter(school=school).order_by('-created_at'),'event_count':Event.objects.filter(school=school,status='published').count(),'pending_count':TicketRequest.objects.filter(event__school=school,status__in=['requested','under_review']).count()+Participation.objects.filter(event__school=school,status='organizer_pending').count(),'approved_count':confirmed_total(Event.objects.filter(school=school)),'announcement_count':Announcement.objects.filter(school=school,status='published').count()})
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
        if not request.member or request.member.role=='organizer': raise Http404()
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
    from .weekly_summary import family_facts
    return render(request,'community/family.html',{'weekly_facts':family_facts(request.parent),'ai_weekly_enabled':bool(settings.ANTHROPIC_API_KEY),'group_bookings':request.parent.bookings.select_related('event','session').order_by('-created_at'),'children':request.parent.children.all(),'participations':items,'plans':plans,'visible_ids':set(public_events(request).values_list('pk',flat=True))})

@parent_required
@require_POST
def family_weekly_summary(request):
    from .weekly_summary import family_facts,commentary
    from django.http import JsonResponse
    facts={**family_facts(request.parent),'locale':'pt-PT' if request.ui_locale=='pt-PT' else 'en'}
    try:answer=commentary(facts)
    except Exception:return JsonResponse({'error':'AI is unavailable; the factual summary remains available.'},status=503)
    response=JsonResponse(answer);response['Cache-Control']='no-store';return response

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
        if plan.event.is_cancelled or (plan.session and plan.session.is_cancelled): continue
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

@login_required
@discovery_view
def session_edit(request,event_id,pk=None):
    with transaction.atomic():
        event=get_object_or_404(Event.objects.select_for_update(),pk=event_id,listing_type='activity')
        from .organizers import can_manage
        if not can_manage(request.user,request.member,event): raise Http404()
        if event.is_cancelled: return HttpResponseForbidden('Cancelled listings cannot add or edit sessions.')
        timezone.activate(ZoneInfo(event.time_zone))
        session=get_object_or_404(ActivitySession.objects.select_for_update(),pk=pk,activity=event) if pk else ActivitySession(activity=event)
        form=SessionForm(request.POST or None,instance=session)
        if request.method=='POST' and form.is_valid():
            item=form.save()
            if item.is_cancelled:
                from .models import FamilyBooking
                for booking in item.family_bookings.filter(status__in=['pending','confirmed']):
                    booking.status='cancelled';booking.save()
                    Notification.objects.create(user=booking.parent.user,school=event.school,kind='family',title='Session cancelled',message='The organizer cancelled this session.',link='/family/')
                for participation in item.participations.exclude(status__in=['cancelled','declined']):
                    from .services import record_participation,participation_notice
                    previous=participation.status;participation.status='cancelled';participation.save();record_participation(participation,previous,request.user);participation_notice(participation,'Session cancelled','The organizer cancelled this session. No other session is reserved automatically.')
            else:
                from .services import participation_notice
                for participation in item.participations.exclude(status__in=['cancelled','declined']): participation_notice(participation,'Activity session updated','Check your family workspace for the latest session details.')
            if request.member.role=='organizer':
                event.status='submitted';event.published_by=None;event.save(update_fields=['status','published_by','updated_at'])
                from .services import staff_notify
                staff_notify(event.school,'Activity sessions awaiting review','An organizer edited activity sessions. Review before publication.','/staff/')
            saved_success(request,'Activity session saved ✦');return redirect('organizer_event' if request.member.role=='organizer' else 'event_edit',pk=event.pk)
    return render(request,'community/form.html',{'form':form,'form_time_zone':event.time_zone,'title':'One session. One little adventure.','eyebrow':event.title,'submit':'Save session ✦','help':'Each session has its own capacity and participation requests. Times use '+event.time_zone+'.'})

@login_required
@discovery_view
@require_POST
def organizer_ai_draft(request):
    if not request.member or not request.member.verified or request.member.role not in ['organizer','staff']:
        return HttpResponseForbidden('Verified organiser or school staff access is required.')
    from .activity_draft import draft_response
    return draft_response(request)

@login_required
@discovery_view
def organizer_workspace(request,pk=None):
    if not request.member or request.member.role!='organizer' or not request.member.verified:
        return HttpResponseForbidden('Verified organiser account required for Organiser Studio.')
    listings=Event.objects.filter(created_by=request.user,school=request.member.school).order_by('-updated_at')
    editing=pk is not None or request.path.endswith('/new/') or request.method=='POST'
    if not editing:
        return render(request,'community/organizer.html',{'listings':listings,'published_count':listings.filter(status='published',is_cancelled=False).count(),'draft_count':listings.filter(status='draft').count(),'review_count':listings.filter(status='submitted').count(),'confirmed_count':confirmed_total(listings)})
    with transaction.atomic():
        event=get_object_or_404(Event.objects.select_for_update(),pk=pk,created_by=request.user,school=request.member.school) if pk else Event(school=request.member.school,created_by=request.user,visibility='public')
        timezone.activate(ZoneInfo(event.time_zone))
        if event.is_cancelled:
            messages.info(request,'Cancelled listings remain closed. Create a new listing for another date.')
            return redirect('organizer_event',pk=event.pk)
        draft=request.POST.get('action')=='draft'
        form=OrganizerSubmissionForm(request.POST or None,request.FILES or None,instance=event,draft=draft)
        if request.method=='POST' and form.is_valid():
            item=form.save(False);item.status='draft' if draft else 'submitted';item.published_by=None;item.identity_verified=False;item.save()
            if not draft:
                from .services import staff_notify
                staff_notify(item.school,'Listing awaiting review','An organizer submitted a listing for publication review.','/staff/')
            saved_success(request,'Draft saved ✦' if draft else 'Submitted for staff review. Nothing was published automatically ✦')
            return redirect('organizer')
    return render(request,'community/organizer_editor.html',{'form':form,'event':event})

@login_required
@discovery_view
def organizer_apply(request):
    if request.member and request.member.role=='organizer' and request.member.verified: return redirect('organizer')
    if request.member and request.member.role in ['student','staff']: return HttpResponseForbidden('Use an adult organizer account. School staff can create listings in their existing workspace.')
    application=OrganizerApplication.objects.filter(user=request.user).first()
    if application:
        return render(request,'community/organizer_application.html',{'application':application})
    form=OrganizerApplicationForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        application=form.save(False);application.user=request.user;application.save()
        from .services import staff_notify
        staff_notify(application.school,'Organizer application','An adult organizer has requested posting access.','/staff/organizers/')
        saved_success(request,'Organizer application saved for staff review ✦');return redirect('organizer_apply')
    return render(request,'community/form.html',{'form':form,'title':'Bring your community together.','eyebrow':'APPLY AS AN ORGANIZER','submit':'Apply for posting access ✦','help':'A school team reviews your organization before granting posting access. This does not automatically verify your identity or background checks.'})

@scoped(staff=True)
def organizer_applications(request):
    return render(request,'community/organizer_applications.html',{'applications':OrganizerApplication.objects.filter(school=request.member.school).select_related('user').order_by('status','created_at')})

@scoped(staff=True)
@require_POST
def organizer_application_review(request,pk):
    get_object_or_404(OrganizerApplication,pk=pk,school=request.member.school)
    from .organizers import review_application
    try: review_application(request.user,request.member,pk,request.POST.get('status'),request.POST.get('note',''));saved_success(request,'Organizer application reviewed ✦')
    except ValueError as e: messages.error(request,str(e))
    return redirect('organizer_applications')

def managed_listing(request,pk):
    from .organizers import can_manage
    event=get_object_or_404(Event,pk=pk)
    if not can_manage(request.user,request.member,event): raise Http404()
    return event

@login_required
@discovery_view
def organizer_event(request,pk):
    event=managed_listing(request,pk)
    timezone.activate(ZoneInfo(event.time_zone))
    family=event.participations.select_related('child','session').all()
    tickets=event.requests.select_related('student').all()
    session=request.GET.get('session','')
    if session:
        family=family.filter(session_id=int(session)) if session.isdigit() and len(session)<12 else family.none()
    status=request.GET.get('status','')
    family_labels=dict(Participation.STATUSES)
    if status in family_labels: family=family.filter(status=status)
    ticket_statuses={'organizer_pending':['requested','under_review'],'confirmed':['approved'],'declined':['declined'],'cancelled':['cancelled'],'interested':[],'parent_pending':[]}
    if status in ticket_statuses: tickets=tickets.filter(status__in=ticket_statuses[status])
    # Interest is shown as an aggregate only. Child identities are shared after parent approval.
    family=family.filter(Q(status__in=['organizer_pending','confirmed'])|Q(history__new_status='organizer_pending')).distinct()
    preview=request.GET.get('preview')=='1'
    return render(request,'community/organizer_event.html',{'group_bookings':event.family_bookings.select_related('parent__user','session').order_by('-created_at'),'event':event,'family_requests':family.order_by('-created_at'),'tickets':tickets.order_by('-created_at'),'interest_count':event.participations.filter(status__in=['interested','parent_pending']).count(),'pending_count':event.participations.filter(status='organizer_pending').count()+event.requests.filter(status__in=['requested','under_review']).count()+event.family_bookings.filter(status='pending').count(),'confirmed_count':confirmed_total(Event.objects.filter(pk=event.pk)),'statuses':Participation.STATUSES,'selected_status':status,'selected_session':session,'preview':preview})

@login_required
@discovery_view
@require_POST
def organizer_decision(request,pk,kind,request_id):
    event=managed_listing(request,pk)
    try:
        if kind=='family':
            get_object_or_404(Participation,pk=request_id,event=event,parent_reviewed_at__isnull=False)
            confirm_participation(request.user,request.member,request_id,request.POST.get('status'),request.POST.get('note',''))
        elif kind=='ticket':
            get_object_or_404(TicketRequest,pk=request_id,event=event)
            decide(request.user,request.member,request_id,request.POST.get('status'),request.POST.get('note',''))
        else: raise Http404()
        saved_success(request,'Participation decision saved ✦')
    except ValueError as e: messages.error(request,str(e))
    return redirect('organizer_event',pk=pk)

@login_required
@discovery_view
@require_POST
def organizer_cancel(request,pk):
    managed_listing(request,pk)
    from .organizers import cancel_listing
    try: cancel_listing(request.user,request.member,pk,request.POST.get('note',''));saved_success(request,'Listing cancelled and affected participants notified in the app.')
    except ValueError as e: messages.error(request,str(e))
    return redirect('organizer_event',pk=pk)

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
    return render(request,'community/finder.html',{'results':results,'error':error,'preferences':preferences,'searched':request.method=='POST' and not error,'ai_configured':bool(settings.ANTHROPIC_API_KEY)})
