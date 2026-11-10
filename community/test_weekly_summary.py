import json
from io import BytesIO
from unittest.mock import patch
from django.core.cache import cache
from django.test import TestCase,override_settings
from django.utils import timezone
from datetime import timedelta
from .weekly_summary import family_facts
from . import test_features as fixtures

@override_settings(ANTHROPIC_API_KEY='test-secret',ANTHROPIC_MODEL='test-model')
class WeeklySummaryTests(TestCase):
    @classmethod
    def setUpTestData(cls):fixtures.FeatureTests.setUpTestData.__func__(cls)
    def setUp(self):cache.clear()
    def payload(self):return {'requested':2,'approved':1,'period':'week','locale':'en'}
    def response(self,text='A little curiosity can be a lovely starting point for your next family adventure.'):
        return BytesIO(json.dumps({'stop_reason':'tool_use','content':[{'type':'tool_use','name':'weekly_commentary','input':{'commentary':text}}]}).encode())
    @patch('community.weekly_summary.urllib.request.urlopen')
    def test_ai_commentary_uses_only_anonymous_counts_and_caches(self,send):
        send.return_value=self.response()
        response=self.client.post('/demo/weekly-summary/',json.dumps(self.payload()),content_type='application/json')
        self.assertEqual(response.status_code,200);self.assertEqual(response.json()['source'],'ai')
        request=json.loads(send.call_args.args[0].data)
        self.assertEqual(json.loads(request['messages'][0]['content']),self.payload())
        self.assertNotIn('Test Child',send.call_args.args[0].data.decode())
        self.assertNotContains(response,'test-secret')
        self.client.post('/demo/weekly-summary/',json.dumps(self.payload()),content_type='application/json');self.assertEqual(send.call_count,1)
    @patch('community.weekly_summary.urllib.request.urlopen')
    def test_numbers_or_invalid_output_are_not_displayed_as_ai(self,send):
        send.return_value=self.response('Your child made 999 requests this week.')
        response=self.client.post('/demo/weekly-summary/',json.dumps(self.payload()),content_type='application/json')
        self.assertEqual(response.status_code,503)
    @override_settings(ANTHROPIC_API_KEY='')
    @patch('community.weekly_summary.urllib.request.urlopen')
    def test_missing_key_keeps_factual_summary_available(self,send):
        self.client.force_login(self.parent)
        response=self.client.get('/family/')
        self.assertContains(response,'Weekly overview');self.assertContains(response,'0 individual activity requests')
        self.assertEqual(self.client.post('/demo/weekly-summary/',json.dumps(self.payload()),content_type='application/json').status_code,503)
        send.assert_not_called()
    @patch('community.weekly_summary.urllib.request.urlopen')
    def test_invalid_counts_and_personal_identifiers_are_rejected(self,send):
        for extra in [{'approved':3},{'requested':True},{'child_name':'Private Child'},{'locale':'unknown'}]:
            with self.subTest(extra=extra):self.assertEqual(self.client.post('/demo/weekly-summary/',json.dumps({**self.payload(),**extra}),content_type='application/json').status_code,400)
        send.assert_not_called()
    def test_live_facts_are_parent_scoped_and_current_week_only(self):
        own=self.pending();other=self.pending(child=self.other_child)
        self.assertEqual(family_facts(self.account)['requested'],1)
        self.assertEqual(family_facts(self.other_account)['requested'],1)
        self.assertEqual(family_facts(self.account)['approved'],1)
        self.event.participations.filter(pk=own.pk).update(created_at=timezone.now()-timedelta(days=14))
        self.assertEqual(family_facts(self.account)['requested'],0)
    def pending(self,child=None):return fixtures.FeatureTests.pending(self,child=child)
    def test_live_endpoint_requires_parent_account(self):
        self.assertEqual(self.client.post('/family/weekly-summary/').status_code,302)
        self.client.force_login(self.staff);self.assertEqual(self.client.post('/family/weekly-summary/').status_code,302)
    @patch('community.weekly_summary.urllib.request.urlopen')
    def test_live_ai_cannot_use_client_supplied_counts_or_other_parent_data(self,send):
        self.pending();self.pending(child=self.other_child)
        send.return_value=self.response();self.client.force_login(self.parent)
        response=self.client.post('/family/weekly-summary/',{'requested':999,'approved':999,'child_name':'Private Child'})
        self.assertEqual(response.status_code,200)
        facts=json.loads(json.loads(send.call_args.args[0].data)['messages'][0]['content'])
        self.assertEqual(facts['requested'],1);self.assertEqual(facts['approved'],1)
        self.assertNotIn('Private Child',send.call_args.args[0].data.decode())
    def test_demo_endpoint_is_post_only_and_csrf_protected(self):
        from django.test import Client
        self.assertEqual(self.client.get('/demo/weekly-summary/').status_code,405)
        self.assertEqual(Client(enforce_csrf_checks=True).post('/demo/weekly-summary/',json.dumps(self.payload()),content_type='application/json').status_code,403)
