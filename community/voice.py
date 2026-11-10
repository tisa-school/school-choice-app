"""Reviewed speech transcripts use the existing server-side Claude search interpreter."""
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .finder import interpret,FinderUnavailable

@require_POST
def voice_filters(request):
    if len(request.body)>3000:return JsonResponse({'error':'Invalid search.'},status=400)
    try:
        data=json.loads(request.body)
        if not isinstance(data,dict) or set(data)!={'preferences','consent'} or data['consent'] is not True or not isinstance(data['preferences'],str) or not 1<=len(data['preferences'].strip())<=500:raise ValueError()
    except (ValueError,TypeError):return JsonResponse({'error':'Review the search and confirm consent.'},status=400)
    try:filters=interpret(data['preferences'].strip())
    except FinderUnavailable:return JsonResponse({'error':'AI search is unavailable. Use the ordinary search filters.'},status=503)
    response=JsonResponse({'filters':filters});response['Cache-Control']='no-store';return response
