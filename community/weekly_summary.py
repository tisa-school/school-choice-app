"""AI adds anonymous commentary; counts and suggestions remain application facts."""
import hashlib
import json
import re
import urllib.request
from datetime import timedelta
from zoneinfo import ZoneInfo
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST


def commentary(facts):
    if not settings.ANTHROPIC_API_KEY:raise RuntimeError()
    key='weekly-comment:'+hashlib.sha256((settings.ANTHROPIC_MODEL+json.dumps(facts,sort_keys=True)).encode()).hexdigest()
    existing=cache.get(key)
    if existing:return existing
    payload={'model':settings.ANTHROPIC_MODEL,'max_tokens':160,'system':
        'Write one short warm sentence of commentary for a parent weekly activity summary, based only on the anonymous counts. '
        'Counts and an eligible activity suggestion are displayed separately by the app. Do not repeat numbers, counts, dates or quantities. '
        'Do not name children, activities, venues or schools. Do not invent outcomes, friendships, abilities, bookings, or safety checks. '
        'If no requests, invite gentle exploration; otherwise acknowledge curiosity. Parent approval is permission, never admission. '
        'Use European Portuguese for pt-PT; otherwise English. Call weekly_commentary.',
        'messages':[{'role':'user','content':json.dumps(facts)}],
        'tools':[{'name':'weekly_commentary','description':'One short grounded sentence, with no personal data or numeric claims.',
                  'input_schema':{'type':'object','additionalProperties':False,'properties':{'commentary':{'type':'string','maxLength':240}},'required':['commentary']}}],
        'tool_choice':{'type':'tool','name':'weekly_commentary'}}
    request=urllib.request.Request('https://api.anthropic.com/v1/messages',data=json.dumps(payload).encode(),headers={'x-api-key':settings.ANTHROPIC_API_KEY,'anthropic-version':'2023-06-01','Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(request,timeout=10) as response:data=json.loads(response.read(16000))
    calls=[b for b in data.get('content',[]) if b.get('type')=='tool_use' and b.get('name')=='weekly_commentary']
    if data.get('stop_reason')!='tool_use' or len(calls)!=1:raise ValueError()
    result=calls[0].get('input',{})
    if set(result)!={'commentary'} or not isinstance(result['commentary'],str) or not 10<=len(result['commentary'].strip())<=240 or re.search(r'\d',result['commentary']):raise ValueError()
    answer={'source':'ai','commentary':result['commentary'].strip()};cache.set(key,answer,900);return answer


def valid_facts(data):
    if not isinstance(data,dict) or set(data)!={'requested','approved','period','locale'}:raise ValueError()
    if type(data['requested'])is not int or type(data['approved'])is not int or not 0<=data['approved']<=data['requested']<=1000:raise ValueError()
    if data['period'] not in {'week','session'} or data['locale'] not in {'en','pt-PT'}:raise ValueError()
    return data

@require_POST
def demo_weekly_summary(request):
    if len(request.body)>1000:return JsonResponse({'error':'Invalid summary.'},status=400)
    try:facts=valid_facts(json.loads(request.body))
    except (ValueError,TypeError,KeyError):return JsonResponse({'error':'Invalid summary.'},status=400)
    try:answer=commentary(facts)
    except Exception:return JsonResponse({'error':'AI is unavailable; the factual summary remains available.'},status=503)
    response=JsonResponse(answer);response['Cache-Control']='no-store';return response


def family_facts(parent):
    """Owner-scoped individual requests, counted in the current Lisbon calendar week."""
    from .models import Participation
    today=timezone.now().astimezone(ZoneInfo('Europe/Lisbon'))
    start=today.replace(hour=0,minute=0,second=0,microsecond=0)-timedelta(days=today.weekday());end=start+timedelta(days=7)
    rows=Participation.objects.filter(child__parent=parent,created_at__gte=start,created_at__lt=end).exclude(status='interested')
    return {'requested':rows.count(),'approved':rows.filter(status__in=['organizer_pending','confirmed']).count(),'period':'week'}
