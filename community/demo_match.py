"""Claude explanations for fictional demo attributes only; no real child records are read."""
import hashlib
import json
import urllib.request
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_POST

LANGUAGES={'en','pt','fr','es','de','it','nl','tr'}
INTERESTS={'Arts','Science','Mathematics','Sports','Nature','Music','Gaming','Shopping','Theater & Drama','Coding','Games','School Life'}

def attributes(data):
    if not isinstance(data,dict) or set(data)!={'age','interests','languages','activity','locale'}:raise ValueError()
    age=data['age'];interests=data['interests'];languages=data['languages'];activity=data['activity']
    if type(age)is not int or not 7<=age<=17:raise ValueError()
    if not isinstance(interests,list) or not 1<=len(interests)<=10 or any(not isinstance(i,str) or i not in INTERESTS for i in interests):raise ValueError()
    if not isinstance(languages,list) or not 1<=len(languages)<=5 or any(not isinstance(i,str) or i not in LANGUAGES for i in languages):raise ValueError()
    if not isinstance(activity,dict) or set(activity)!={'interest','minAge','maxAge','languages'}:raise ValueError()
    if activity['interest'] not in INTERESTS or type(activity['minAge'])is not int or type(activity['maxAge'])is not int or not 0<=activity['minAge']<=activity['maxAge']<=17:raise ValueError()
    if not isinstance(activity['languages'],list) or len(activity['languages'])>7 or any(not isinstance(i,str) or i not in LANGUAGES for i in activity['languages']):raise ValueError()
    if data['locale'] not in {'en','pt-PT'}:raise ValueError()
    return data

def explanation(data):
    age_fit=data['activity']['minAge']<=data['age']<=data['activity']['maxAge']
    interest_fit=data['activity']['interest'] in data['interests']
    language_fit=bool(set(data['languages'])&set(data['activity']['languages']))
    score=40*age_fit+40*interest_fit+20*language_fit
    if not settings.ANTHROPIC_API_KEY:raise RuntimeError()
    key='demo-match:'+hashlib.sha256((settings.ANTHROPIC_MODEL+json.dumps(data,sort_keys=True)).encode()).hexdigest()
    existing=cache.get(key)
    if existing:return existing
    facts={**data,'age_fit':age_fit,'interest_fit':interest_fit,'language_fit':language_fit}
    payload={'model':settings.ANTHROPIC_MODEL,'max_tokens':250,'system':
        'Write one short, warm sentence explaining an activity match for a fictional child. Use only the supplied facts. '
        'Mention the child age, interest match or new interest, and language compatibility. If outside the age range, clearly say so. '
        'Never claim friendship, safety, verification, bookings, or guaranteed suitability. No child names, venue or personal data. '
        'Write in English for en, European Portuguese for pt-PT. Call match_explanation.',
        'messages':[{'role':'user','content':json.dumps(facts)}],
        'tools':[{'name':'match_explanation','description':'A friendly factual explanation.',
                  'input_schema':{'type':'object','additionalProperties':False,'properties':{'explanation':{'type':'string','maxLength':400}},'required':['explanation']}}],
        'tool_choice':{'type':'tool','name':'match_explanation'}}
    request=urllib.request.Request('https://api.anthropic.com/v1/messages',data=json.dumps(payload).encode(),headers={
        'x-api-key':settings.ANTHROPIC_API_KEY,'anthropic-version':'2023-06-01','Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(request,timeout=10) as response:result=json.loads(response.read(16000))
    calls=[c for c in result.get('content',[]) if c.get('type')=='tool_use' and c.get('name')=='match_explanation']
    if result.get('stop_reason')!='tool_use' or len(calls)!=1:raise ValueError()
    output=calls[0].get('input',{})
    if set(output)!={'explanation'} or not isinstance(output['explanation'],str) or not 10<=len(output['explanation'].strip())<=400:raise ValueError()
    answer={'source':'ai','explanation':output['explanation'].strip(),'percentage':score,'age_eligible':age_fit}
    cache.set(key,answer,600)
    return answer

@require_POST
def demo_match(request):
    if len(request.body)>2000:return JsonResponse({'error':'Invalid demo attributes.'},status=400)
    try:data=attributes(json.loads(request.body))
    except (ValueError,TypeError,KeyError):return JsonResponse({'error':'Invalid demo attributes.'},status=400)
    try:answer=explanation(data)
    except Exception:return JsonResponse({'error':'AI matching is unavailable. A profile-based explanation is still shown.'},status=503)
    response=JsonResponse(answer);response['Cache-Control']='no-store';return response
