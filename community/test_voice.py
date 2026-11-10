import json
from unittest.mock import patch
from django.test import TestCase,Client
from .finder import validate_filters,FinderUnavailable,recommendations
from .test_features import FeatureTests

class VoiceSearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):FeatureTests.setUpTestData.__func__(cls)
    @patch('community.voice.interpret',return_value={'age':'','categories':['Arts','Sports'],'category':''})
    def test_reviewed_transcript_returns_filters_without_creating_events(self,interpret):
        before=self.event.__class__.objects.count()
        response=self.client.post('/demo/voice-filters/',json.dumps({'preferences':'I like drawing and football','consent':True}),content_type='application/json')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['filters']['categories'],['Arts','Sports'])
        interpret.assert_called_once_with('I like drawing and football')
        self.assertEqual(self.event.__class__.objects.count(),before)
    @patch('community.voice.interpret')
    def test_consent_and_payload_limits_checked_before_provider(self,interpret):
        for data in [{'preferences':'Art','consent':False},{'preferences':'','consent':True},{'preferences':'x'*501,'consent':True},{'preferences':'Art','consent':True,'audio':'not accepted'}]:
            self.assertEqual(self.client.post('/demo/voice-filters/',json.dumps(data),content_type='application/json').status_code,400)
        interpret.assert_not_called()
    @patch('community.voice.interpret',side_effect=FinderUnavailable('secret raw provider body'))
    def test_unavailable_ai_keeps_errors_safe(self,interpret):
        response=self.client.post('/demo/voice-filters/',json.dumps({'preferences':'Art','consent':True}),content_type='application/json')
        self.assertEqual(response.status_code,503);self.assertNotContains(response,'secret',status_code=503)
    def test_endpoint_requires_post_and_csrf(self):
        self.assertEqual(self.client.get('/demo/voice-filters/').status_code,405)
        self.assertEqual(Client(enforce_csrf_checks=True).post('/demo/voice-filters/',{},content_type='application/json').status_code,403)
    def test_multiple_interests_match_any_authorized_category(self):
        filters=validate_filters({'category':'','categories':['Arts','Sports'],'age':11})
        self.assertEqual(filters['category'],'')
        results=recommendations(self.parent,filters)
        self.assertIn(self.event.pk,[item['event'].pk for item in results])
        self.assertNotIn(self.private.pk,[item['event'].pk for item in results])
        with self.assertRaises(ValueError):validate_filters({'categories':['not an interest']})
