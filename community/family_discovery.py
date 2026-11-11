"""Independent activity and school discovery; existing booking workflows stay authoritative."""
import json
import random
from datetime import timedelta
from urllib.parse import urlencode,urlsplit
from uuid import uuid4
from zoneinfo import ZoneInfo
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q,Prefetch,F
from django.http import JsonResponse,HttpResponseBadRequest
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST,require_GET
from .discovery import discovery_view,visible_events,filter_listings,LANGUAGES
from .directory_forms import ActivityDiscoveryForm,SchoolSearchForm,SchoolProfileForm,AGE_GROUPS,INTERESTS
from .models import Event,ActivitySession,SavedEvent,SchoolProfile,ShortlistedSchool,SaveReceipt


def weekend_dates():
    today=timezone.now().astimezone(ZoneInfo('Europe/Lisbon')).date()
    saturday=today+timedelta(days=(5-today.weekday())%7)
    if today.weekday()==6:saturday=today-timedelta(days=1)
    return saturday,saturday+timedelta(days=1)


def activity_results(user,values):
    form=ActivityDiscoveryForm(values)
    if not form.is_valid():return form,[]
    data=form.cleaned_data
    basics={k:data.get(k) or '' for k in ['q','age','category','area','price','environment','language']}
    query=filter_listings(visible_events(user).filter(is_cancelled=False),basics)
    if data.get('age_group'):
        low,high=map(int,data['age_group'].split('-'));query=query.filter(min_age__lte=high,max_age__gte=low)
    if data.get('max_price') is not None:query=query.filter(price_amount__lte=data['max_price'])
    query=query.prefetch_related(Prefetch('sessions',queryset=ActivitySession.objects.filter(is_cancelled=False,start_at__gt=timezone.now()).order_by('start_at'),to_attr='discovery_sessions'))
    start,end=data.get('date_from'),data.get('date_to')
    weekend=weekend_dates() if data.get('weekend') else None
    results=[]
    for event in query:
        targets=event.discovery_sessions if event.listing_type=='activity' else ([event] if event.start_at>timezone.now() else [])
        eligible=[]
        for target in targets:
            day=timezone.localtime(target.start_at,ZoneInfo(event.time_zone)).date()
            if start and day<start or end and day>end:continue
            if weekend and not weekend[0]<=day<=weekend[1]:continue
            eligible.append(target)
        if not eligible and (event.listing_type=='event' or start or end or weekend):continue
        event.discovery_next_at=eligible[0].start_at if eligible else None
        event.discovery_session=eligible[0] if eligible and event.listing_type=='activity' else None
        results.append(event)
    results.sort(key=lambda e:(e.discovery_next_at is None,e.discovery_next_at or timezone.now(),e.pk))
    return form,results


def activity_choices(user):
    query=visible_events(user).filter(is_cancelled=False)
    return {'activity_categories':list(query.values_list('category',flat=True).distinct()),'activity_areas':list(query.exclude(area='').values_list('area',flat=True).distinct()),'age_groups':AGE_GROUPS,'interests':INTERESTS,'activity_languages':LANGUAGES}


@discovery_view
@require_GET
def discovery_home(request):
    _,weekend=activity_results(request.user,{'weekend':'on'})
    return render(request,'discovery/home.html',{'weekend_activities':weekend[:6],**activity_choices(request.user),'school_count':SchoolProfile.objects.filter(is_published=True).count(),'saved_ids':set(SavedEvent.objects.filter(user=request.user).values_list('event_id',flat=True)) if request.user.is_authenticated else set()})


@discovery_view
@require_GET
def activities(request):
    form,results=activity_results(request.user,request.GET)
    query=request.GET.copy();query.pop('surprise',None)
    back='/discover/activities/'+('?' + query.urlencode() if query else '')
    if request.GET.get('surprise') and results:
        event=random.choice(results)
        return redirect('/events/'+str(event.pk)+'/?'+urlencode({'return_to':back}))
    context={'form':form,'activity_results':results,'result_count':len(results),'discovery_back':back,'surprise_empty':bool(request.GET.get('surprise')) and not results,'active_filters':[(form.fields[k].label,v) for k,v in request.GET.items() if k in form.fields and v],'saved_ids':set(SavedEvent.objects.filter(user=request.user).values_list('event_id',flat=True)) if request.user.is_authenticated else set(),**activity_choices(request.user)}
    return render(request,'discovery/activities.html',context)


def filtered_schools(values):
    form=SchoolSearchForm(values);query=SchoolProfile.objects.filter(is_published=True)
    if not form.is_valid():return form,query.none()
    data=form.cleaned_data
    if data.get('city'):query=query.filter(city__iexact=data['city'])
    if data.get('q'):query=query.filter(Q(name__icontains=data['q'])|Q(city__icontains=data['q'])|Q(neighbourhood__icontains=data['q'])|Q(address__icontains=data['q']))
    if data.get('age_group'):
        low,high=map(int,data['age_group'].split('-'));query=query.filter(min_age__lte=high,max_age__gte=low)
    if data.get('school_type'):query=query.filter(school_type=data['school_type'])
    if data.get('stage'):query=query.filter(stages__regex=rf"(^|,){data['stage']}(,|$)")
    if data.get('language'):query=query.filter(languages__regex=rf"(^|,){data['language']}(,|$)")
    if data.get('curriculum'):query=query.filter(curriculum__icontains=data['curriculum'])
    if data.get('max_fee') is not None:query=query.filter(annual_fee_from__lte=data['max_fee']).exclude(fee_year='')
    sort=data.get('sort')
    if sort=='name_desc':query=query.order_by('-name')
    elif sort=='recent':query=query.order_by(F('last_checked').desc(nulls_last=True),'name')
    elif sort=='fee':query=query.order_by(F('annual_fee_from').asc(nulls_last=True),'name')
    return form,query


@discovery_view
@require_GET
def schools(request):
    form,profiles=filtered_schools(request.GET)
    if form.is_valid():
        selected=form.cleaned_data
        for profile in profiles:
            reasons=[]
            if selected.get('age_group'):reasons.append('Age range overlaps '+selected['age_group'])
            if selected.get('school_type'):reasons.append(profile.get_school_type_display())
            if selected.get('language'):reasons.append('Teaching language: '+dict(LANGUAGES).get(selected['language'],selected['language']))
            if selected.get('stage'):reasons.append(dict(SchoolProfile.STAGES)[selected['stage']])
            if selected.get('curriculum'):reasons.append(profile.curriculum)
            if selected.get('max_fee') is not None:reasons.append('Published starting annual fee is within your filter; confirm grade-specific costs.')
            profile.match_reasons=reasons
    return render(request,'discovery/schools.html',{'school_form':form,'school_results':profiles,'school_saved':set(ShortlistedSchool.objects.filter(user=request.user).values_list('profile_id',flat=True)) if request.user.is_authenticated else set(),'school_curricula':SchoolProfile.objects.filter(is_published=True).exclude(curriculum='').values_list('curriculum',flat=True).distinct(),'school_active':[(form.fields[k].label,v) for k,v in request.GET.items() if k in form.fields and v]})


@discovery_view
@require_GET
def school_detail(request,slug):
    profile=get_object_or_404(SchoolProfile,is_published=True,slug=slug)
    back=request.GET.get('return_to','')
    try:
        parsed=urlsplit(back)
        if parsed.netloc or parsed.scheme or parsed.path not in ['/schools/','/saved/','/schools/compare/']:back='/schools/'
    except ValueError:back='/schools/'
    return render(request,'discovery/school_detail.html',{'school_profile':profile,'school_back':back,'school_saved':set(ShortlistedSchool.objects.filter(user=request.user,profile=profile).values_list('profile_id',flat=True)) if request.user.is_authenticated else set()})


@discovery_view
@require_GET
def compare_schools(request):
    slugs=list(dict.fromkeys(request.GET.getlist('school')))
    if len(slugs)>3:return HttpResponseBadRequest('Choose up to three schools to compare.')
    profiles={p.slug:p for p in SchoolProfile.objects.filter(is_published=True,slug__in=slugs)}
    selected=[profiles[s] for s in slugs if s in profiles]
    fields=[('Location','location'),('Ages','age_label'),('School type','type'),('Educational stages','stage_labels'),('Teaching languages','language_labels'),('Curriculum','curriculum'),('School hours','hours'),('Facilities','facilities'),('Extracurricular activities','extracurriculars'),('Annual fees','fees'),('Academic year','fee_year'),('Fee coverage','fee_includes'),('Admissions','admissions'),('Source','source_name'),('Last checked','last_checked')]
    rows=[]
    for label,field in fields:
        values=[]
        for p in selected:
            if field=='location':value=', '.join(s for s in [p.neighbourhood,p.city] if s)
            elif field=='type':value=p.get_school_type_display()
            elif field=='fees':value=(f'From €{p.annual_fee_from:,.2f} / year'+(f' to €{p.annual_fee_to:,.2f}' if p.annual_fee_to is not None else '')) if p.annual_fee_from is not None and p.fee_year else ''
            else:value=getattr(p,field)
            values.append(value or 'Not provided')
        rows.append((label,values))
    return render(request,'discovery/compare.html',{'compare_profiles':selected,'compare_rows':rows,'missing_profiles':len(selected)<len(slugs)})


@login_required
@require_POST
@discovery_view
def save_choice(request,kind,key):
    try:
        data=json.loads(request.body)
        if not isinstance(data,dict) or set(data)!={'saved'} or type(data['saved'])is not bool:raise ValueError()
    except (ValueError,TypeError):return JsonResponse({'error':'Choose a valid save action.'},status=400)
    if kind=='school':
        item=get_object_or_404(SchoolProfile,is_published=True,slug=key);model=ShortlistedSchool;lookup={'user':request.user,'profile':item}
    elif kind=='activity' and key.isdigit():
        item=get_object_or_404(visible_events(request.user),pk=int(key));model=SavedEvent;lookup={'user':request.user,'event':item}
    else:return JsonResponse({'error':'Unknown item.'},status=404)
    with transaction.atomic():
        if data['saved']:model.objects.get_or_create(**lookup)
        else:model.objects.filter(**lookup).delete()
        SaveReceipt.objects.update_or_create(user=request.user,defaults={'action':('Saved ' if data['saved'] else 'Removed saved ')+('school shortlist item.' if kind=='school' else 'activity.')})
    response=JsonResponse({'saved':data['saved']});response['Cache-Control']='no-store';return response


def saved_context(request):
    if request.user.is_authenticated:
        events=visible_events(request.user).filter(savedevent__user=request.user)
        profiles=SchoolProfile.objects.filter(is_published=True,shortlisted_by__user=request.user)
    else:
        ids=[int(s) for s in request.GET.get('activities','').split(',')[:100] if s.isdigit() and len(s)<12]
        slugs=[s for s in request.GET.get('schools','').split(',')[:100] if len(s)<=190]
        events=visible_events(request.user).filter(pk__in=ids)
        profiles=SchoolProfile.objects.filter(is_published=True,slug__in=slugs)
    for event in events:
        session=event.sessions.filter(is_cancelled=False,start_at__gt=timezone.now()).order_by('start_at').first() if event.listing_type=='activity' else None
        event.discovery_next_at=session.start_at if session else event.start_at if event.listing_type=='event' else None
    return {'school_return':'/saved/','discovery_back':'/saved/','activity_results':events,'school_results':profiles,'saved_ids':set(events.values_list('pk',flat=True)),'school_saved':set(profiles.values_list('pk',flat=True))}


@discovery_view
@require_GET
def saved_fragment(request):
    response=render(request,'discovery/saved_fragment.html',saved_context(request));response['Cache-Control']='private, no-store';return response


@login_required
@discovery_view
def manage_school(request):
    # Staff authority is checked here so a membership role cannot be supplied by POST.
    if not request.member or request.member.role!='staff' or not request.member.verified:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('Verified school staff access is required.')
    profile=SchoolProfile.objects.filter(school=request.member.school).first() or SchoolProfile(school=request.member.school,name=request.member.school.name)
    form=SchoolProfileForm(request.POST or None,instance=profile)
    if request.method=='POST' and form.is_valid():
        item=form.save(commit=False)
        if not item.slug:item.slug=slugify(item.name)[:150]+'-'+uuid4().hex[:8]
        item.school=request.member.school;item.save()
        from .persistence import saved_success
        saved_success(request,'School profile saved.');return redirect('manage_school_profile')
    return render(request,'community/form.html',{'form':form,'title':'Your school, accurately represented.','eyebrow':'SOURCED SCHOOL DIRECTORY','submit':'Save school profile','help':'Publish only facts supported by the stated source. Leave unavailable details blank; families will see Not provided.'})
