"""One visibility policy for browsing, saving, media, AI, and family actions."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from functools import wraps
from django.db.models import Q
from django.utils import timezone
from .models import Event, Membership

LANGUAGES = [('en','English'),('pt','Portuguese'),('fr','French'),('es','Spanish'),('de','German'),('it','Italian'),('nl','Dutch')]

def membership(user):
    return Membership.objects.select_related('school').filter(user=user).first() if user.is_authenticated else None

def visible_events(user):
    member=membership(user)
    scope=Q(visibility='public',published_by__isnull=False)
    if member:
        if member.role=='organizer':
            if member.verified: scope |= Q(school=member.school,created_by=user)
        else: scope |= Q(school=member.school)
    return Event.objects.filter(scope,status='published').select_related('school')

def discovery_view(view):
    @wraps(view)
    def wrapped(request,*args,**kwargs):
        request.member=membership(request.user)
        timezone.activate(ZoneInfo(request.member.school.time_zone if request.member else 'Europe/Lisbon'))
        if request.member:
            from .services import publish_due
            publish_due(request.member.school)
        return view(request,*args,**kwargs)
    return wrapped

def filter_listings(queryset, values):
    q=values.get('q','').strip()[:200]
    if q: queryset=queryset.filter(Q(title__icontains=q)|Q(description__icontains=q)|Q(venue__icontains=q)|Q(organizer__icontains=q))
    category=values.get('category','All')
    if category and category!='All': queryset=queryset.filter(category=category)
    age=values.get('age','')
    if age:
        if str(age).isdigit() and len(str(age))<=2 and int(age)<=17: queryset=queryset.filter(min_age__lte=int(age),max_age__gte=int(age))
        else: queryset=queryset.none()
    language=values.get('language','')
    if language in dict(LANGUAGES): queryset=queryset.filter(languages__regex=rf'(^|,){language}(,|$)')
    area=values.get('area','').strip()[:100]
    if area: queryset=queryset.filter(area__icontains=area)
    environment=values.get('environment','')
    if environment in ['indoor','outdoor','mixed']: queryset=queryset.filter(activity_environment=environment)
    if values.get('available')=='1':
        ids=[]
        for event in queryset:
            if event.listing_type=='event' and event.eligible: ids.append(event.pk)
            elif event.listing_type=='activity' and not event.is_cancelled and event.ticket_requests_enabled and (not event.requests_close_at or event.requests_close_at>timezone.now()):
                if any(session.remaining!=0 for session in event.sessions.filter(is_cancelled=False,start_at__gt=timezone.now())): ids.append(event.pk)
        queryset=queryset.filter(pk__in=ids)
    price=values.get('price','')
    if price=='free': queryset=queryset.filter(price_amount=0)
    elif price=='paid': queryset=queryset.filter(price_amount__gt=0)
    elif price=='unknown': queryset=queryset.filter(price_amount__isnull=True,price_text='')
    if values.get('visibility') in ('public','school'): queryset=queryset.filter(visibility=values['visibility'])
    day=values.get('day','')
    if day:
        try:
            date=datetime.strptime(day,'%Y-%m-%d').date()
            # Day boundaries are evaluated in each listing's own time zone, including DST.
            ids=[]
            for item in queryset:
                tz=ZoneInfo(item.time_zone)
                if item.listing_type=='event': matches=timezone.localtime(item.start_at,tz).date()==date
                else: matches=any(timezone.localtime(session.start_at,tz).date()==date for session in item.sessions.filter(is_cancelled=False))
                if matches: ids.append(item.pk)
            queryset=queryset.filter(pk__in=ids)
        except ValueError: queryset=queryset.none()
    return queryset.distinct()
