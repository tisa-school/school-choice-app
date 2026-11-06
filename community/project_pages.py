import calendar
import json
from datetime import datetime,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404,HttpResponseForbidden
from django.shortcuts import render,redirect,get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from .discovery import discovery_view,visible_events
from .localization import text,REQUESTED_LOCALES,ACTIVE_LOCALES
from .forms import FeedbackForm
from .models import Feedback,Membership

@discovery_view
def about(request):
    folder=settings.BASE_DIR/'content'
    project=json.loads((folder/'project.json').read_text())
    content=json.loads((folder/'about.json').read_text()).get(request.ui_locale)
    return render(request,'community/about.html',{'project':project,'about':content,'students':[p for p in project['contributors'] if p['group']=='students'],'lead':next(p for p in project['contributors'] if p['group']=='lead'),'coordinators':[p for p in project['contributors'] if p['group']=='coordination'],'leadership':[p for p in project['contributors'] if p['group']=='leadership'],'language_roadmap':[item for item in REQUESTED_LOCALES if item[0] not in ACTIVE_LOCALES]})

@discovery_view
def feedback(request):
    listing=None
    raw=request.GET.get('listing','')
    if raw:
        if not raw.isdigit() or len(raw)>12: raise Http404()
        listing=get_object_or_404(visible_events(request.user),pk=int(raw))
    form=FeedbackForm(request.POST or None,user=request.user,initial={'listing':listing,'kind':'report' if listing else 'feedback'})
    if request.method=='POST' and form.is_valid():
        item=form.save(False)
        item.submitted_by=request.user if request.user.is_authenticated else None
        item.school=item.listing.school if item.listing else None
        item.save()
        return redirect('feedback_received')
    return render(request,'community/feedback.html',{'form':form,'listing':listing})

@discovery_view
def feedback_received(request): return render(request,'community/feedback_received.html')

@login_required
@discovery_view
def feedback_inbox(request):
    member=request.member
    if not member or member.role!='staff' or not member.verified: return HttpResponseForbidden('Verified school staff access is required.')
    rows=Feedback.objects.filter(school=member.school).select_related('listing').order_by('status','-created_at')
    return render(request,'community/feedback_inbox.html',{'feedback_items':rows})

@login_required
@discovery_view
@require_POST
def feedback_review(request,pk):
    member=request.member
    if not member or member.role!='staff' or not member.verified: return HttpResponseForbidden('Verified school staff access is required.')
    item=get_object_or_404(Feedback,pk=pk,school=member.school)
    status=request.POST.get('status')
    if status not in ['reviewed','resolved']: return HttpResponseForbidden('Invalid review status.')
    item.status=status;item.review_note=request.POST.get('note','')[:500];item.reviewed_by=request.user;item.reviewed_at=timezone.now();item.save()
    from .persistence import saved_success
    saved_success(request,text('Feedback review saved.'))
    return redirect('feedback_inbox')

@discovery_view
def event_calendar(request):
    value=request.GET.get('month','')
    try:
        current=datetime.strptime(value,'%Y-%m').date() if value and len(value)==7 else timezone.localdate().replace(day=1)
        if not 2000<=current.year<=2100: raise ValueError()
    except ValueError: current=timezone.localdate().replace(day=1)
    current=current.replace(day=1)
    upcoming=(current.replace(day=28)+timedelta(days=4)).replace(day=1)
    entries={}
    for event in visible_events(request.user).filter(is_cancelled=False).prefetch_related('sessions'):
        targets=[event] if event.listing_type=='event' else event.sessions.filter(is_cancelled=False)
        for target in targets:
            date=timezone.localtime(target.start_at,ZoneInfo(event.time_zone)).date()
            if date.year==current.year and date.month==current.month:
                entries.setdefault(date.day,[]).append({'event':event,'start_at':target.start_at,'session':event.listing_type=='activity'})
    weeks=[[{'day':day,'entries':entries.get(day,[])} for day in week] for week in calendar.monthcalendar(current.year,current.month)]
    from django.utils.formats import date_format
    weekdays=[date_format(datetime(2026,11,2)+timedelta(days=i),'D') for i in range(7)]
    return render(request,'community/calendar.html',{'weekdays':weekdays,'weeks':weeks,'month':current,'previous':(current-timedelta(days=1)).strftime('%Y-%m'),'next':upcoming.strftime('%Y-%m')})
