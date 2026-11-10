"""Stateless catalogue assistant. No chat history, profiles or messages are persisted."""
import json
import re
from datetime import timedelta
from zoneinfo import ZoneInfo
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from .finder import interpret, recommendations, FinderUnavailable


def reply(data, status=200):
    response = JsonResponse(data, status=status)
    response['Cache-Control'] = 'no-store'
    return response


@require_POST
def ask_tk(request):
    if len(request.body) > 3000:
        return reply({'error': 'invalid'}, 400)
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict) or set(data) != {'preferences', 'consent', 'scope', 'mode'}:
            raise ValueError()
        question = data['preferences']
        if not isinstance(question, str) or len(question) > 500 or data['scope'] not in ('demo', 'live') or data['mode'] not in ('ai', 'browse'):
            raise ValueError()
        if data['mode'] == 'ai' and (data['consent'] is not True or not question.strip()):
            raise ValueError()
        if data['mode'] == 'browse' and question:
            raise ValueError()
    except (ValueError, TypeError):
        return reply({'error': 'invalid'}, 400)
    # Obvious contact information is rejected before any provider call. The UI also
    # asks users to submit activity preferences only; this is not a complete PII detector.
    contact_text = re.sub(r'\b\d{4}-\d{2}-\d{2}\b', '', question)
    if re.search(r'@|https?://|(?:\+?\d[\s().-]*){7,}', contact_text):
        return reply({'error': 'private'}, 400)
    try:
        filters = interpret(question.strip()) if data['mode'] == 'ai' else {}
    except FinderUnavailable:
        return reply({'error': 'unavailable'}, 503)
    # A weekend is a pair of dates, never an invented single day. Resolve locally
    # using Lisbon's calendar, even if the interpreter supplies one weekday.
    weekend = bool(re.search(r'\bweekend\b|fim[ -]de[ -]semana', question, re.I))
    days = []
    if weekend:
        today = timezone.now().astimezone(ZoneInfo('Europe/Lisbon')).date()
        saturday = today + timedelta(days=(5-today.weekday()) % 7)
        if today.weekday() == 6:
            saturday = today - timedelta(days=1)
        days = [str(saturday), str(saturday + timedelta(days=1))]
        filters['day'] = ''
    results = []
    if data['scope'] == 'live':
        seen = set()
        for day in days or [filters.get('day', '')]:
            for match in recommendations(request.user, {**filters, 'day': day}):
                event = match['event']
                if event.pk in seen:
                    continue
                seen.add(event.pk)
                results.append({'title': event.title, 'url': f'/events/{event.pk}/', 'reason': match['reason']})
    return reply({'source': 'ai' if data['mode'] == 'ai' else 'catalogue',
                  'filters': filters, 'days': days, 'results': results[:4]})
