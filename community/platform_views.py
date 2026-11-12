"""Production discovery and private planning; demonstrations use a separate read-only seed."""
import calendar
import json
from datetime import datetime,date,timedelta
from urllib.parse import urlencode
from zoneinfo import ZoneInfo
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction,IntegrityError
from django.db.models import Q
from django.http import Http404,HttpResponse
from django.shortcuts import render,redirect,get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET,require_POST
from .models import Event,SchoolProfile,ExperienceListing,SavedExperience,SavedEvent,ShortlistedSchool,ParentAccount,PrivateFamilyEvent,FamilyPlan,EventExperience,SiteConfiguration
from .discovery import discovery_view,visible_events
from .directory_forms import ActivityDiscoveryForm,SchoolSearchForm,AGE_GROUPS
from .family_discovery import activity_results,filtered_schools
from .management_forms import PrivateFamilyEventForm
from .views import parent_required
from .localization import text
from .persistence import saved_success

THEMES=[('sports','Football & Sports',['Sports']),('art','Art & Creativity',['Arts']),('science','Science & Technology',['Science','Coding','Technology']),('culture','Museums & Culture',['Museums & Culture','School Life']),('nature','Nature & Outdoors',['Nature']),('music','Music & Performing Arts',['Music','Theater & Drama']),('visits','Educational Visits',['Educational Visits','Entrepreneurship']),('family','Family Weekends',['Family Weekends','School Life','Shopping'])]

@discovery_view
@require_GET
def home(request):
    _,activities=activity_results(request.user,{})
    parent=ParentAccount.objects.filter(user=request.user).first() if request.user.is_authenticated else None
    plans=FamilyPlan.objects.filter(parent=parent,event__in=visible_events(request.user),event__start_at__gte=timezone.now()).select_related('event','session')[:3] if parent else []
    return render(request,'platform/home.html',{'featured_activities':activities[:6],'featured_schools':SchoolProfile.objects.filter(is_published=True,archived=False)[:3],'featured_experiences':ExperienceListing.objects.filter(is_published=True,archived=False).order_by('-last_verified')[:3],'age_groups':AGE_GROUPS,'themes':THEMES,'upcoming_plans':plans,'has_family':bool(parent)})


def experience_results(values):
    form=ActivityDiscoveryForm(values)
    query=ExperienceListing.objects.filter(is_published=True,archived=False)
    if not form.is_valid():return query.none()
    data=form.cleaned_data
    if data.get('q'):
        q=data['q'];query=query.filter(Q(title__icontains=q)|Q(description__icontains=q)|Q(organizer__icontains=q)|Q(area__icontains=q)|Q(category__icontains=q))
    if data.get('age') is not None:query=query.filter(min_age__lte=data['age'],max_age__gte=data['age'])
    if data.get('environment'):query=query.filter(environment=data['environment'])
    if data.get('category'):query=query.filter(category=data['category'])
    if data.get('theme'):query=query.filter(category__in=next((cats for code,label,cats in THEMES if code==data['theme']),[]))
    if data.get('area'):query=query.filter(area__icontains=data['area'])
    if data.get('language'):query=query.filter(languages__regex=rf"(^|,){data['language']}(,|$)")
    if data.get('age_group'):
        low,high=map(int,data['age_group'].split('-'));query=query.filter(min_age__lte=high,max_age__gte=low)
    # Open-ended experiences do not claim a scheduled date or a time-specific availability.
    if data.get('date_from') or data.get('date_to') or data.get('weekend'):return query.none()
    if data.get('price')=='free':query=query.filter(price_amount=0)
    if data.get('price')=='paid':query=query.filter(price_amount__gt=0)
    if data.get('price')=='unknown':query=query.filter(price_amount__isnull=True)
    if data.get('max_price') is not None:query=query.filter(price_amount__lte=data['max_price'])
    return query.order_by('-updated_at','title') if data.get('sort')=='recent' else query.order_by('title')

@discovery_view
@require_GET
def search(request):
    form,activities=activity_results(request.user,request.GET)
    school_values={key:request.GET.get(key,'') for key in ['q','age_group','language','curriculum','school_type','stage']}
    school_form,schools=filtered_schools(school_values)
    if request.GET.get('area'):schools=schools.filter(Q(city__icontains=request.GET['area'][:100])|Q(neighbourhood__icontains=request.GET['area'][:100])|Q(address__icontains=request.GET['area'][:100]))
    experiences=experience_results(request.GET)
    community=EventExperience.objects.filter(status='published',event__in=visible_events(request.user)).select_related('event').order_by('-created_at')
    if request.GET.get('q'):community=community.filter(body__icontains=request.GET['q'][:200])
    if not form.is_valid():community=community.none();schools=schools.none()
    if form.is_valid():
        data=form.cleaned_data
        if data.get('category'):community=community.filter(event__category=data['category'])
        if data.get('area'):community=community.filter(event__area__icontains=data['area'])
        if data.get('age_group'):
            low,high=map(int,data['age_group'].split('-'));community=community.filter(event__min_age__lte=high,event__max_age__gte=low)
        if data.get('language'):community=community.filter(event__languages__regex=rf"(^|,){data['language']}(,|$)")
    kind=request.GET.get('kind','all')
    if kind not in ['all','activities','schools','community']:kind='all'
    return render(request,'platform/search.html',{'search_form':form,'school_search_form':school_form,'activity_results':activities if kind in ['all','activities'] else [],'school_results':schools if kind in ['all','schools'] else [],'experience_results':experiences if kind in ['all','activities'] else [],'community_results':community[:30] if kind in ['all','community'] else [],'kind':kind,'discovery_back':'/search/?'+request.GET.urlencode(),'age_groups':AGE_GROUPS,'themes':THEMES})

@discovery_view
def experience_detail(request,slug):
    experience=get_object_or_404(ExperienceListing,slug=slug,is_published=True,archived=False)
    from urllib.parse import urlsplit
    back=request.GET.get('return_to','')
    try:
        parsed=urlsplit(back)
        if parsed.scheme or parsed.netloc or parsed.path not in ['/discover/activities/','/saved/','/search/']:back='/discover/activities/'
    except ValueError:back='/discover/activities/'
    saved=request.user.is_authenticated and SavedExperience.objects.filter(user=request.user,experience=experience).exists()
    return render(request,'platform/experience_detail.html',{'experience_back':back,'experience':experience,'experience_saved':saved,'map_url':'https://www.openstreetmap.org/search?'+urlencode({'query':experience.address or experience.area})})

@login_required
@require_POST
def save_experience(request,pk):
    item=get_object_or_404(ExperienceListing,pk=pk,is_published=True,archived=False)
    if request.POST.get('action')=='remove':SavedExperience.objects.filter(user=request.user,experience=item).delete()
    else:SavedExperience.objects.get_or_create(user=request.user,experience=item)
    from .persistence import saved_success
    saved_success(request,'Saved items updated.');return redirect('experience_detail',slug=item.slug)

@discovery_view
def my_family(request):
    if request.user.is_authenticated and ParentAccount.objects.filter(user=request.user).exists():return redirect('family')
    return render(request,'platform/family_welcome.html',{})

@parent_required
def family_calendar_view(request):
    today=timezone.localdate();mode=request.GET.get('view','month');mode=mode if mode in ['month','week'] else 'month'
    try:selected=date.fromisoformat(request.GET.get('date',today.isoformat()))
    except ValueError:selected=today
    if mode=='month':
        weeks=calendar.Calendar(firstweekday=0).monthdatescalendar(selected.year,selected.month);days=[day for week in weeks for day in week]
        previous=(selected.replace(day=1)-timedelta(days=1)).replace(day=1);following=(selected.replace(day=28)+timedelta(days=4)).replace(day=1)
    else:
        first=selected-timedelta(days=selected.weekday());days=[first+timedelta(days=i) for i in range(7)];previous=selected-timedelta(days=7);following=selected+timedelta(days=7)
    entries=[]
    for item in PrivateFamilyEvent.objects.filter(parent=request.parent,start_at__date__gte=days[0],start_at__date__lte=days[-1]).order_by('start_at'):
        entries.append({'date':timezone.localtime(item.start_at).date(),'time':item.start_at,'title':item.title,'edit_url':f'/family/private-events/{item.pk}/','private':True})
    for plan in FamilyPlan.objects.filter(parent=request.parent,event__in=visible_events(request.user)).select_related('event','session'):
        target=plan.session or plan.event;day=timezone.localtime(target.start_at).date()
        if days[0]<=day<=days[-1]:entries.append({'date':day,'time':target.start_at,'title':plan.event.title,'detail_url':f'/events/{plan.event_id}/','cancelled':plan.event.is_cancelled or bool(plan.session and plan.session.is_cancelled),'plan_id':plan.pk})
    cells=[{'day':day,'today':day==today,'other_month':day.month!=selected.month,'entries':sorted([entry for entry in entries if entry['date']==day],key=lambda e:e['time'])} for day in days]
    return render(request,'platform/family_calendar.html',{'calendar_cells':cells,'calendar_mode':mode,'selected_date':selected,'previous_date':previous,'next_date':following})

@parent_required
@transaction.atomic
def private_event_edit(request,pk=None):
    item=get_object_or_404(PrivateFamilyEvent,pk=pk,parent=request.parent) if pk else PrivateFamilyEvent(parent=request.parent)
    experience=None
    if not pk and request.GET.get('experience'):experience=get_object_or_404(ExperienceListing,pk=request.GET['experience'],is_published=True,archived=False);item.experience=experience
    form=PrivateFamilyEventForm(request.POST or None,instance=item,initial={'title':experience.title} if experience else {})
    if request.method=='POST' and form.is_valid():
        duplicate=PrivateFamilyEvent.objects.filter(parent=request.parent,title=form.cleaned_data['title'],start_at=form.cleaned_data['start_at'],end_at=form.cleaned_data['end_at']).exclude(pk=item.pk).exists()
        if duplicate:form.add_error(None,'This family calendar entry already exists.')
        else:
            try:
                with transaction.atomic():form.save()
            except IntegrityError:form.add_error(None,'This family calendar entry already exists.')
            else:saved_success(request,'Private calendar entry saved. No booking has been made.');return redirect('family_calendar_view')
    return render(request,'platform/private_event_form.html',{'form':form,'calendar_event':item,'experience':experience or item.experience})

@parent_required
@require_POST
@transaction.atomic
def private_event_delete(request,pk):
    get_object_or_404(PrivateFamilyEvent,pk=pk,parent=request.parent).delete();saved_success(request,'Calendar entry removed.');return redirect('family_calendar_view')

@discovery_view
def information(request,page):
    if page not in ['help','privacy','terms','safety']:raise Http404()
    return render(request,'platform/information.html',{'information_page':page})

@require_GET
def product_tour(request):
    admin=request.path.startswith('/manage/')
    if admin:
        from .community_views import moderator
        if not moderator(request.user):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden('An authorised administrator account is required.')
    from django.contrib.auth.models import AnonymousUser
    _,events=activity_results(AnonymousUser(),{})
    seed={'events':[{'id':str(e.pk),'title':e.title,'category':e.category,'area':e.area} for e in events[:12]],'schools':[{'id':str(s.pk),'name':s.name,'city':s.city,'curriculum':s.curriculum} for s in SchoolProfile.objects.filter(is_published=True,archived=False)[:12]],'administrator':admin}
    return render(request,'platform/tour.html',{'tour_seed':seed})
