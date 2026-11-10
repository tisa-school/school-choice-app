import json
from io import BytesIO
from unittest.mock import patch
from django.core.cache import cache
from django.test import TestCase,Client,override_settings
from .demo_match import explanation

@override_settings(ANTHROPIC_API_KEY='fake-server-secret',ANTHROPIC_MODEL='claude-haiku-4-5-20251001')
class DemoMatchTests(TestCase):
    def setUp(self):cache.clear()
    def payload(self):return {'age':11,'interests':['Arts','Science'],'languages':['en'],'activity':{'interest':'Arts','minAge':8,'maxAge':16,'languages':['en','pt']},'locale':'en'}
    def response(self,text='At 11, art fits your interests and age group, with English available to help you feel comfortable.'):
        return BytesIO(json.dumps({'stop_reason':'tool_use','content':[{'type':'tool_use','name':'match_explanation','input':{'explanation':text}}]}).encode())
    def post(self,data):return self.client.post('/demo/ai-match/',json.dumps(data),content_type='application/json')
    @patch('community.demo_match.urllib.request.urlopen')
    def test_ai_explanation_badge_data_and_factual_score(self,send):
        send.return_value=self.response();r=self.post(self.payload())
        self.assertEqual(r.status_code,200);self.assertEqual(r.json()['source'],'ai');self.assertEqual(r.json()['percentage'],100)
        request=send.call_args.args[0];payload=json.loads(request.data)
        self.assertEqual(request.full_url,'https://api.anthropic.com/v1/messages')
        self.assertNotIn('fake-server-secret',r.content.decode());self.assertNotIn('Emma',request.data.decode())
        self.assertEqual(payload['tool_choice']['name'],'match_explanation')
        self.assertEqual(self.post(self.payload()).json(),r.json());self.assertEqual(send.call_count,1)
    @patch('community.demo_match.urllib.request.urlopen')
    def test_age_mismatch_cannot_claim_full_match(self,send):
        send.return_value=self.response('The art and English match your interests, but this activity is outside your age group.')
        data=self.payload();data['activity']['minAge']=12
        r=self.post(data).json();self.assertEqual(r['percentage'],60);self.assertFalse(r['age_eligible'])
    @override_settings(ANTHROPIC_API_KEY='')
    @patch('community.demo_match.urllib.request.urlopen')
    def test_missing_key_never_claims_ai(self,send):
        r=self.post(self.payload());self.assertEqual(r.status_code,503);self.assertNotIn('source',r.json());send.assert_not_called()
    @patch('community.demo_match.urllib.request.urlopen',side_effect=TimeoutError('fake-server-secret'))
    def test_no_credits_timeout_or_bad_provider_response_is_safe(self,send):
        r=self.post(self.payload());self.assertEqual(r.status_code,503);self.assertNotContains(r,'fake-server-secret',status_code=503)
        send.side_effect=None;send.return_value=BytesIO(b'{"stop_reason":"max_tokens","content":[]}')
        self.assertEqual(self.post(self.payload()).status_code,503)
    @patch('community.demo_match.urllib.request.urlopen')
    def test_personal_identifiers_or_invalid_inputs_are_rejected(self,send):
        for patch_data in [{'name':'Emma'},{'age':True},{'languages':['private@email.test']},{'interests':['personal info']},{'locale':'unsupported'}]:
            with self.subTest(patch=patch_data):self.assertEqual(self.post({**self.payload(),**patch_data}).status_code,400)
        send.assert_not_called()
    def test_post_only_and_csrf_protected(self):
        self.assertEqual(self.client.get('/demo/ai-match/').status_code,405)
        self.assertEqual(Client(enforce_csrf_checks=True).post('/demo/ai-match/',json.dumps(self.payload()),content_type='application/json').status_code,403)
        response=self.client.get('/demo/events/art-afternoon/')
        self.assertContains(response,'name="csrf-token"');self.assertIn('csrftoken',response.cookies)
