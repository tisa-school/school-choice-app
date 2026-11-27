"""Versioned bearer-only mobile API. Existing website cookie/CSRF rules are untouched."""
import hashlib
import json
import secrets
from datetime import timedelta
from functools import wraps
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db import transaction, IntegrityError
from django.http import JsonResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from .models import (MobileSession,MobilePushDevice,MobileDeletionRequest,ParentAccount,
 ChildProfile,SavedEvent,ShortlistedSchool,SchoolProfile,Event,FamilyPlan,Participation,
 PrivateFamilyEvent,Notification,Announcement,Feedback,TicketRequest,Collection)
from .discovery import visible_events,membership
from .family_discovery import activity_results,filtered_schools
from .forms import SignupForm,ChildProfileForm,ProfileForm
from .management_forms import PrivateFamilyEventForm
from .persistence import record_saved_change,receipt_payload
from .services import express_interest,parent_decision,request_ticket
from .mobile_push import configured as push_configured

class MobileError(Exception):
    def __init__(self,message,status=400):self.message=message;self.status=status

def digest(value):return hashlib.sha256(value.encode()).hexdigest()

def endpoint(methods=('GET',),private=False):
    def decorate(view):
        @csrf_exempt
        @wraps(view)
        def wrapped(request,*args,**kwargs):
            if not settings.MOBILE_API_ENABLED:return JsonResponse({'error':'Mobile API is not enabled on this server.'},status=404)
            origin=request.headers.get('Origin')
            if origin and origin not in settings.MOBILE_ALLOWED_ORIGINS:return JsonResponse({'error':'Origin not allowed.'},status=403)
            def finish(response):
                response['Cache-Control']='private, no-store';response['Vary']='Origin, Authorization'
                response['X-Content-Type-Options']='nosniff'
                if origin:
                    response['Access-Control-Allow-Origin']=origin
                    response['Access-Control-Allow-Methods']=', '.join(methods)+', OPTIONS'
                    response['Access-Control-Allow-Headers']='Authorization, Content-Type'
                return response
            if request.method=='OPTIONS':return finish(HttpResponse(status=204))
            if request.method not in methods:return finish(JsonResponse({'error':'Method not allowed.'},status=405))
            # Never fall back to the website's authenticated cookie session.
            request.user=AnonymousUser();request.mobile_session=None
            auth=request.headers.get('Authorization','')
            if auth:
                raw=auth.removeprefix('Bearer ')
                session=MobileSession.objects.select_related('user').filter(token_hash=digest(raw),revoked=False,expires_at__gt=timezone.now(),user__is_active=True).first() if auth.startswith('Bearer ') and 20<len(raw)<200 else None
                if not session:return finish(JsonResponse({'error':'Please sign in again.'},status=401))
                request.mobile_session=session;request.user=session.user
            if private and not request.user.is_authenticated:return finish(JsonResponse({'error':'Sign in to continue.'},status=401))
            try:
                request.mobile_data={}
                if request.method in ('POST','PUT','DELETE'):
                    if len(request.body)>32768:raise MobileError('Request too large.',413)
                    if request.content_type!='application/json':raise MobileError('Use application/json.',415)
                    try:request.mobile_data=json.loads(request.body or b'{}')
                    except (ValueError,UnicodeDecodeError):raise MobileError('Invalid JSON.')
                    if not isinstance(request.mobile_data,dict):raise MobileError('Use a JSON object.')
                response=view(request,*args,**kwargs)
            except MobileError as error:response=JsonResponse({'error':error.message},status=error.status)
            except TypeError:response=JsonResponse({'error':'Check the supplied field types.'},status=400)
            except IntegrityError:response=JsonResponse({'error':'This change conflicts with an existing record. Refresh and try again.'},status=409)
            except ObjectDoesNotExist:response=JsonResponse({'error':'The requested record is not available.'},status=404)
            except Http404:response=JsonResponse({'error':'Not found.'},status=404)
            except (ValueError,ValidationError) as error:response=JsonResponse({'error':' '.join(error.messages) if isinstance(error,ValidationError) else str(error)},status=400)
            return finish(response)
        return wrapped
    return decorate

def data(request):return request.mobile_data

def require_parent(request):
    parent=ParentAccount.objects.filter(user=request.user).first()
    if not parent:raise MobileError('Only a parent or guardian can manage family participation.',403)
    return parent

def user_data(user):
    member=membership(user);parent=ParentAccount.objects.filter(user=user).exists()
    role='staff' if user.is_superuser else member.role if member else 'parent' if parent else 'member'
    return {'id':user.pk,'name':user.first_name or user.username,'role':role,'parent':parent,'school':member.school.name if member else None,'verified':bool(user.is_superuser or member and member.verified)}

def issue(user,platform):
    if platform not in ('ios','android','web'):raise MobileError('Invalid platform.')
    raw=secrets.token_urlsafe(48);expiry=timezone.now()+timedelta(days=settings.MOBILE_SESSION_DAYS)
    MobileSession.objects.create(user=user,platform=platform,token_hash=digest(raw),expires_at=expiry)
    return JsonResponse({'token':raw,'expires_at':expiry.isoformat(),'user':user_data(user)})

def event_data(event,user):
    return {'id':event.pk,'title':event.title,'description':event.description,'category':event.category,
      'venue':event.venue,'area':event.area,'start_at':event.start_at.isoformat(),'end_at':event.end_at.isoformat() if event.end_at else None,
      'ages':f'{event.min_age}–{event.max_age}' if event.min_age is not None else 'Ask the organiser',
      'languages':event.languages,'price':str(event.price_amount)+' EUR' if event.price_amount is not None else event.price_text or 'Price on request',
      'cancelled':event.is_cancelled,'accessibility':event.accessibility,'listing_type':event.listing_type,
      'public':bool(event.visibility=='public' and event.published_by_id and event.status=='published' and not event.archived),
      'saved':bool(user.is_authenticated and SavedEvent.objects.filter(user=user,event=event).exists()),
      'sessions':[{'id':s.pk,'start_at':s.start_at.isoformat(),'end_at':s.end_at.isoformat(),'venue':s.venue} for s in event.sessions.filter(is_cancelled=False,start_at__gt=timezone.now())[:40]] if event.listing_type=='activity' else [],
      'web_path':f'/events/{event.pk}/'}

def school_data(school,user):
    return {'id':school.pk,'slug':school.slug,'name':school.name,'city':school.city,'summary':school.summary,'curriculum':school.curriculum,
      'public':True,'address':school.address,'hours':school.hours,'fee_includes':school.fee_includes,'fees':'From '+str(school.annual_fee_from)+' EUR' if school.annual_fee_from is not None and school.fee_year else 'Not supplied','fee_year':school.fee_year,
      'ages':school.age_label or 'Not provided','languages':school.language_labels,'source':school.source_name,
      'last_checked':str(school.last_checked) if school.last_checked else None,'website':school.website,
      'saved':bool(user.is_authenticated and ShortlistedSchool.objects.filter(user=user,profile=school).exists()),'web_path':f'/schools/{school.slug}/'}

@endpoint()
def capabilities(request):return JsonResponse({'version':1,'brand':'TK-ZONE','authentication':'bearer','push_configured':{'ios':push_configured('ios'),'android':push_configured('android')},'privacy_path':'/privacy/','account_deletion':'request-with-password'})

@endpoint(('POST',))
@transaction.atomic
def login(request):
    body=data(request);username=body.get('username');password=body.get('password')
    if not isinstance(username,str) or not isinstance(password,str) or len(username)>254 or len(password)>1024:raise MobileError('Unable to sign in.',401)
    user=authenticate(request,username=username.strip(),password=password)
    if not user:raise MobileError('Unable to sign in. Check your credentials or use account recovery.',401)
    return issue(user,body.get('platform','web'))

@endpoint(('POST',))
@transaction.atomic
def signup(request):
    body=data(request)
    if body.get('guardian_consent') is not True:raise MobileError('An adult parent or guardian must create the account and accept responsibility.')
    form=SignupForm({k:body.get(k,'') for k in ['name','email','password1','password2']})
    if not form.is_valid():raise MobileError('Account could not be created. Check your details or use account recovery.')
    from django.contrib.auth.models import User
    from django.db.models import Q
    if User.objects.filter(Q(username__iexact=form.cleaned_data['email'])|Q(email__iexact=form.cleaned_data['email'])).exists():raise MobileError('Account could not be created. Check your details or use account recovery.')
    user=form.save();ParentAccount.objects.create(user=user)
    return issue(user,body.get('platform','web'))

@endpoint(('POST',),private=True)
@transaction.atomic
def logout(request):
    request.mobile_session.revoked=True;request.mobile_session.save(update_fields=['revoked']);MobilePushDevice.objects.filter(session=request.mobile_session).delete()
    return JsonResponse({'signed_out':True})

@endpoint(('GET','POST'),private=True)
@transaction.atomic
def me(request):
    if request.method=='POST':
        name=data(request).get('name')
        if not isinstance(name,str) or not 1<=len(name.strip())<=100:raise MobileError('Use a display name of 1–100 characters.')
        request.user.first_name=name.strip();request.user.save(update_fields=['first_name']);record_saved_change(request,'Profile saved.')
    return JsonResponse({'user':user_data(request.user)})

@endpoint()
def events(request):
    form,items=activity_results(request.user,request.GET)
    if not form.is_valid():raise MobileError('Check the activity filters.')
    return JsonResponse({'items':[event_data(e,request.user) for e in items[:80]],'count':len(items)})

@endpoint()
def event_detail(request,pk):return JsonResponse({'event':event_data(get_object_or_404(visible_events(request.user),pk=pk),request.user)})

@endpoint(('POST',),private=True)
@transaction.atomic
def save_event(request,pk):
    event=get_object_or_404(visible_events(request.user),pk=pk);saved=data(request).get('saved')
    if type(saved)is not bool:raise MobileError('Choose a valid save action.')
    if saved:SavedEvent.objects.get_or_create(user=request.user,event=event)
    else:SavedEvent.objects.filter(user=request.user,event=event).delete()
    receipt=record_saved_change(request,'Saved activities updated.')
    return JsonResponse({'saved':saved,'save_receipt':receipt_payload(receipt)})

@endpoint(('POST',),private=True)
@transaction.atomic
def ticket(request,pk):
    member=membership(request.user)
    if not member or member.role!='student':raise MobileError('Only school students can request a school ticket.',403)
    get_object_or_404(visible_events(request.user),pk=pk)
    item=request_ticket(request.user,member,pk);record_saved_change(request,'Ticket requested; approval is required.')
    return JsonResponse({'id':item.pk,'status':item.status},status=201)

@endpoint()
def schools(request):
    form,items=filtered_schools(request.GET)
    if not form.is_valid():raise MobileError('Check the school filters.')
    return JsonResponse({'items':[school_data(s,request.user) for s in items[:80]]})

@endpoint()
def public_event(request,pk):
    event=get_object_or_404(Event,pk=pk,visibility='public',published_by__isnull=False,status='published',archived=False)
    return JsonResponse({'event':event_data(event,AnonymousUser())})

@endpoint()
def school_detail(request,pk):
    school=get_object_or_404(SchoolProfile,pk=pk,is_published=True,archived=False)
    return JsonResponse({'school':school_data(school,AnonymousUser())})

@endpoint()
def school_compare(request):
    raw=request.GET.get('ids','').split(',')
    if not 2<=len(raw)<=3 or any(not x.isdigit() or len(x)>12 for x in raw) or len(set(raw))!=len(raw):raise MobileError('Choose two or three different schools.')
    ids=[int(x) for x in raw]
    schools={x.pk:x for x in SchoolProfile.objects.filter(pk__in=ids,is_published=True,archived=False)}
    if len(schools)!=len(ids):raise Http404()
    return JsonResponse({'items':[school_data(schools[pk],AnonymousUser()) for pk in ids]})

@endpoint(('POST',),private=True)
@transaction.atomic
def save_school(request,slug):
    school=get_object_or_404(SchoolProfile,slug=slug,is_published=True,archived=False);saved=data(request).get('saved')
    if type(saved)is not bool:raise MobileError('Choose a valid save action.')
    if saved:ShortlistedSchool.objects.get_or_create(user=request.user,profile=school)
    else:ShortlistedSchool.objects.filter(user=request.user,profile=school).delete()
    record_saved_change(request,'School shortlist updated.');return JsonResponse({'saved':saved})

@endpoint(private=True)
def saved(request):return JsonResponse({'events':[event_data(e,request.user) for e in visible_events(request.user).filter(savedevent__user=request.user)[:80]],'schools':[school_data(s,request.user) for s in SchoolProfile.objects.filter(is_published=True,archived=False,shortlisted_by__user=request.user)[:80]]})

@endpoint(private=True)
def family(request):
    parent=require_parent(request)
    requests=Participation.objects.filter(child__parent=parent).select_related('child','event','session')
    return JsonResponse({'children':[{'id':c.pk,'nickname':c.nickname,'age_band':c.age_band,'interests':c.interests,'languages':c.languages} for c in parent.children.all()],
      'requests':[{'id':r.pk,'child':r.child.nickname,'event':event_data(r.event,request.user),'status':r.status,'note':r.decision_note} for r in requests if visible_events(request.user).filter(pk=r.event_id).exists()]})

@endpoint(('POST','PUT','DELETE'),private=True)
@transaction.atomic
def child(request,pk=None):
    parent=require_parent(request);item=get_object_or_404(ChildProfile,pk=pk,parent=parent) if pk else ChildProfile(parent=parent)
    if request.method=='DELETE':
        if not pk:raise Http404()
        item.delete();record_saved_change(request,'Child profile deleted.');return JsonResponse({'deleted':True})
    form=ChildProfileForm({k:data(request).get(k,'') for k in ['nickname','age_band','interests','languages']},instance=item)
    if not form.is_valid():raise MobileError('Check the nickname, age band and interests.')
    form.save();record_saved_change(request,'Private child profile saved.');return JsonResponse({'id':item.pk})

@endpoint(('POST',),private=True)
@transaction.atomic
def participation(request):
    require_parent(request);body=data(request)
    try:child_id=int(body.get('child_id'));event_id=int(body.get('event_id'));session_id=int(body['session_id']) if body.get('session_id') else None
    except (ValueError,TypeError):raise MobileError('Choose a child and an activity.')
    get_object_or_404(ChildProfile,pk=child_id,parent__user=request.user);get_object_or_404(visible_events(request.user),pk=event_id)
    item=express_interest(request.user,event_id,child_id,session_id)
    parent_decision(request.user,item.pk,'send');record_saved_change(request,'Participation request saved; approval is required.')
    return JsonResponse({'id':item.pk,'status':'parent_pending'},status=201)

@endpoint(('POST',),private=True)
@transaction.atomic
def decision(request,pk):
    require_parent(request);get_object_or_404(Participation,pk=pk,child__parent__user=request.user)
    action=data(request).get('action');password=data(request).get('password','')
    if action not in ('send','approve','decline','cancel') or not isinstance(password,str) or len(password)>1024:raise MobileError('Choose a valid decision and password.')
    item=parent_decision(request.user,pk,action,password)
    record_saved_change(request,'Parent decision saved.');return JsonResponse({'status':item.status})

@endpoint(('GET','POST','DELETE'),private=True)
@transaction.atomic
def calendar(request,pk=None):
    parent=require_parent(request)
    if request.method=='DELETE':
        get_object_or_404(PrivateFamilyEvent,pk=pk,parent=parent).delete();record_saved_change(request,'Calendar entry removed.');return JsonResponse({'deleted':True})
    if request.method=='POST':
        event_id=data(request).get('event_id')
        if event_id:
            event=get_object_or_404(visible_events(request.user),pk=event_id)
            if event.listing_type!='event':raise MobileError('Use the website to choose a recurring activity session.')
            FamilyPlan.objects.get_or_create(parent=parent,event=event)
        else:
            item=get_object_or_404(PrivateFamilyEvent,pk=pk,parent=parent) if pk else PrivateFamilyEvent(parent=parent)
            form=PrivateFamilyEventForm(data(request),instance=item)
            if not form.is_valid():raise MobileError('Provide a title and valid start/end times.')
            if PrivateFamilyEvent.objects.filter(parent=parent,title=form.cleaned_data['title'],start_at=form.cleaned_data['start_at'],end_at=form.cleaned_data['end_at']).exclude(pk=item.pk).exists():raise MobileError('This calendar entry already exists.')
            form.save()
        record_saved_change(request,'Calendar plan saved. This is not a booking.');return JsonResponse({'saved':True})
    entries=[]
    for plan in parent.plans.select_related('event','session'):
        if visible_events(request.user).filter(pk=plan.event_id).exists():
            event=plan.event;target=plan.session or event
            entries.append({'id':'plan-'+str(plan.pk),'title':event.title,'start_at':target.start_at.isoformat(),'end_at':target.end_at.isoformat() if target.end_at else None,'location':target.venue,'cancelled':event.is_cancelled or getattr(target,'is_cancelled',False),'web_path':f'/events/{event.pk}/'})
    for entry in PrivateFamilyEvent.objects.filter(parent=parent):entries.append({'id':'private-'+str(entry.pk),'title':entry.title,'start_at':entry.start_at.isoformat(),'end_at':entry.end_at.isoformat(),'location':'','cancelled':False,'web_path':'/family/'})
    return JsonResponse({'items':entries})

@endpoint(private=True)
def inbox(request):return JsonResponse({'items':[{'id':n.pk,'title':n.title,'message':n.message,'created_at':n.created_at.isoformat(),'read':n.is_read,'web_path':n.link if n.link.startswith('/') and not n.link.startswith('//') else '/notifications/'} for n in Notification.objects.filter(user=request.user).order_by('-created_at')[:80]]})

@endpoint(('POST',),private=True)
@transaction.atomic
def read_notification(request,pk):
    item=get_object_or_404(Notification,pk=pk,user=request.user);item.is_read=True;item.save(update_fields=['is_read']);return JsonResponse({'read':True})

@endpoint(private=True)
def announcements(request):
    member=membership(request.user)
    items=Announcement.objects.filter(school=member.school,status='published').order_by('-is_pinned','-published_at')[:50] if member else []
    return JsonResponse({'items':[{'id':a.pk,'title':a.title,'body':a.body,'pinned':a.is_pinned} for a in items]})

@endpoint(('POST',),private=True)
@transaction.atomic
def report(request):
    message=data(request).get('message','')
    if not isinstance(message,str) or not 10<=len(message.strip())<=2000:raise MobileError('Describe your concern in 10–2000 characters.')
    event=get_object_or_404(visible_events(request.user),pk=data(request).get('event_id')) if data(request).get('event_id') else None
    Feedback.objects.create(kind='report',message=message.strip(),listing=event,school=event.school if event else None,submitted_by=request.user)
    record_saved_change(request,'Report saved for administrator review.');return JsonResponse({'reported':True},status=201)

@endpoint(('POST','DELETE'),private=True)
@transaction.atomic
def push_device(request):
    if request.method=='DELETE':MobilePushDevice.objects.filter(session=request.mobile_session).delete();return JsonResponse({'registered':False})
    who=user_data(request.user)
    if not (who['parent'] or who['verified'] and who['role'] in ('staff','organizer')):raise MobileError('Push notification setup is controlled by adults.',403)
    token=data(request).get('token');platform=request.mobile_session.platform
    if platform not in ('ios','android') or data(request).get('consent') is not True or not isinstance(token,str) or not 20<=len(token)<=4096:raise MobileError('A native token and explicit opt-in are required.')
    MobilePushDevice.objects.update_or_create(session=request.mobile_session,defaults={'user':request.user,'token':token,'platform':platform,'enabled':True})
    return JsonResponse({'registered':True,'delivery_configured':push_configured(platform)})

@endpoint(('POST',),private=True)
@transaction.atomic
def deletion_request(request):
    password=data(request).get('password','')
    if not isinstance(password,str) or len(password)>1024 or not request.user.check_password(password):raise MobileError('Confirm your account password.',403)
    item,_=MobileDeletionRequest.objects.get_or_create(user=request.user,status='pending')
    MobilePushDevice.objects.filter(user=request.user).delete();MobileSession.objects.filter(user=request.user).update(revoked=True)
    return JsonResponse({'requested':True,'request_id':item.pk,'message':'Deletion request recorded for administrator review. Your mobile sessions have been revoked; deletion is not yet complete.'},status=202)
