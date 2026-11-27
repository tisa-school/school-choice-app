"""Optional discovery preferences. The questionnaire never grants account permissions."""
import json
from django import forms
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render,redirect
from django.views.decorators.http import require_http_methods,require_POST
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from .localization import ACTIVE_LOCALES,text
from .models import DiscoveryPreference

INTERESTS=[('Technology','Technology'),('Science','Science'),('Sports','Sports'),('Music','Music'),('Arts','Art'),('Education','Education'),('Nature','Nature')]
KINDS=[('workshop','Workshops'),('open_day','School open days'),('competition','Competitions'),('exhibition','Exhibitions'),('educational','Educational events')]
class PreferenceForm(forms.Form):
    language=forms.ChoiceField(choices=[(k,v[0]) for k,v in ACTIVE_LOCALES.items()])
    audience=forms.ChoiceField(required=False,choices=[('student','Student'),('parent','Parent'),('teacher','Teacher')])
    interests=forms.MultipleChoiceField(required=False,choices=INTERESTS)
    event_kinds=forms.MultipleChoiceField(required=False,choices=KINDS)
    city=forms.CharField(required=False,max_length=100)
    attendance=forms.ChoiceField(required=False,choices=[('online','Online'),('in_person','In person'),('both','Both')])
    budget=forms.ChoiceField(required=False,choices=[('free','Free events'),('both','Free and paid events')])
    def clean_city(self):return ' '.join(self.cleaned_data['city'].split())

def preferences_for(request):
    if request.user.is_authenticated:
        item=DiscoveryPreference.objects.filter(user=request.user).first()
        if item:return item.answers,item.completed
    stored=request.session.get('tk_discovery_preferences',{})
    if request.user.is_authenticated and stored.get('completed'):
        form=PreferenceForm(stored.get('answers',{}))
        if form.is_valid():DiscoveryPreference.objects.get_or_create(user=request.user,defaults={'answers':form.cleaned_data,'completed':True})
    return stored.get('answers',{}),stored.get('completed',False)

@require_http_methods(['GET','POST'])
@transaction.atomic
def settings_view(request):
    answers,completed=preferences_for(request)
    form=PreferenceForm(request.POST or None,initial={**answers,'language':getattr(request,'ui_locale','en')})
    if request.method=='POST' and form.is_valid():
        save_preferences(request,form.cleaned_data)
        return redirect(reverse('discovery_preferences')+'?lang='+form.cleaned_data['language'])
    labels={'language':'Choose language','audience':'Your role','interests':'Interests','event_kinds':'Event types','city':'City or region','attendance':'Attendance preference','budget':'Price'}
    for name,field in form.fields.items():
        field.label=text(labels[name])
        if hasattr(field,'choices'):field.choices=[(k,text(v)) for k,v in field.choices]
    return render(request,'preferences/settings.html',{'form':form,'preferences_saved':request.session.pop('tk_preferences_saved',False)})

def save_preferences(request,answers):
    record={'answers':answers,'completed':True}
    request.session['tk_discovery_preferences']=record
    request.session['tk_preferences_saved']=True
    if not request.user.is_authenticated:request.session.set_expiry(31536000)
    if request.user.is_authenticated:
        from .models import InterfacePreference
        DiscoveryPreference.objects.update_or_create(user=request.user,defaults={'answers':answers,'completed':True})
        InterfacePreference.objects.update_or_create(user=request.user,defaults={'language':answers['language']})
        from .persistence import record_saved_change
        record_saved_change(request,text('Preferences saved.'))

@require_POST
@transaction.atomic
def complete(request):
    if len(request.body)>10000:return JsonResponse({'error':text('Preferences could not be saved. Please try again.')},status=413)
    try:body=json.loads(request.body)
    except (ValueError,UnicodeDecodeError):body=None
    if not isinstance(body,dict):return JsonResponse({'error':text('Preferences could not be saved. Please try again.')},status=400)
    if body.get('skip') is True:
        # Keep only the interface language when the optional questions are skipped.
        body={'language':getattr(request,'ui_locale','en')}
    allowed={'language','audience','interests','event_kinds','city','attendance','budget'}
    if set(body)-allowed:return JsonResponse({'error':text('Check your answers.')},status=400)
    scalar=('language','audience','city','attendance','budget')
    arrays=('interests','event_kinds')
    if any(k in body and not isinstance(body[k],str) for k in scalar) or any(k in body and (not isinstance(body[k],list) or any(not isinstance(v,str) for v in body[k])) for k in arrays):return JsonResponse({'error':text('Check your answers.')},status=400)
    form=PreferenceForm(body)
    if not form.is_valid():return JsonResponse({'error':text('Check your answers.')},status=400)
    save_preferences(request,form.cleaned_data)
    response=JsonResponse({'saved':True,'language':form.cleaned_data['language']})
    response.set_cookie('tkzone_language',form.cleaned_data['language'],max_age=31536000,httponly=True,secure=request.is_secure(),samesite='Lax')
    response['Cache-Control']='private, no-store'
    return response

def normalize_area(value):
    value=value.casefold().strip()
    return {'lisboa':'lisbon','lisbonne':'lisbon','lissabon':'lisbon','лиссабон':'lisbon','里斯本':'lisbon','लिस्बन':'lisbon','লিসবন':'lisbon','لشبونة':'lisbon','لزبن':'lisbon','lizbon':'lisbon'}.get(value,value)

def recommendations_for(request,limit=6):
    answers,completed=preferences_for(request)
    if not completed or not any(answers.get(k) for k in ['interests','event_kinds','city','attendance','budget']):return []
    from .family_discovery import activity_results
    _,candidates=activity_results(request.user,{})
    results=[]
    interests=set(answers.get('interests',[]));
    categories=set().union(*[{'Technology':{'Technology','Coding'},'Education':{'School Life','Educational Visits'},'Arts':{'Arts','Theater & Drama','Museums & Culture'}}.get(i,{i}) for i in interests]) if interests else set()
    kinds=set(answers.get('event_kinds',[]))
    for event in candidates:
        if event.ticket_requests_enabled and event.requests_close_at and event.requests_close_at<=timezone.now():continue
        if answers.get('budget')=='free' and event.price_amount!=0:continue
        score=0;reasons=[]
        if event.category in categories:score+=5;reasons.append(text('Matches your interests'))
        city=normalize_area(answers.get('city',''))
        if city and (city in normalize_area(event.city) or city in normalize_area(event.area)):score+=4;reasons.append(text('Matches your preferred area'))
        if event.event_kind in kinds:score+=3;reasons.append(text('Matches your event types'))
        if answers.get('attendance') in ('online','in_person') and event.attendance_mode in (answers['attendance'],'hybrid'):score+=3;reasons.append(text('Matches your attendance preference'))
        if answers.get('budget')=='free' and event.price_amount==0:score+=2;reasons.append(text('Free event'))
        if not score:continue
        target=next((s for s in event.discovery_sessions if s.capacity is None or s.remaining!=0),None) if event.listing_type=='activity' else (event if event.capacity is None or event.remaining!=0 else None)
        if not target:continue
        event.discovery_next_at=target.start_at
        results.append({'event':event,'score':score,'reason':' · '.join(reasons)})
    results.sort(key=lambda x:(-x['score'],x['event'].discovery_next_at or x['event'].start_at,x['event'].pk))
    return results[:limit]

def onboarding_context(request):
    _,completed=preferences_for(request)
    return {'show_discovery_onboarding':getattr(settings,'DISCOVERY_ONBOARDING_ENABLED',True) and not completed and (request.path in ['/','/saved/','/finder/'] or request.path.startswith(('/discover/activities/','/events/','/schools/'))),
        'onboarding_languages':[(k,v[0]) for k,v in ACTIVE_LOCALES.items()],
        'onboarding_audiences':[('student','Student'),('parent','Parent'),('teacher','Teacher')],'onboarding_interests':INTERESTS,'onboarding_kinds':KINDS}
