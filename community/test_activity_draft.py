import json
from io import BytesIO
from unittest.mock import patch
from django.test import TestCase,Client,override_settings
from . import test_features as fixtures
from .models import Event,Membership,User

@override_settings(ANTHROPIC_API_KEY='test-server-secret',ANTHROPIC_MODEL='test-model')
class ActivityDraftTests(TestCase):
    @classmethod
    def setUpTestData(cls):fixtures.FeatureTests.setUpTestData.__func__(cls)
    brief='An English art workshop for ages 8–12 with step-free access.'
    def output(self):return {'title':{'en':'Creative Art Workshop','pt':'Oficina de arte criativa'},'description':{'en':'Explore drawing in a welcoming art workshop.','pt':'Explora o desenho numa oficina de arte acolhedora.'},'accessibility':{'en':'Step-free access.','pt':'Acesso sem degraus.'},'min_age':8,'max_age':12,'category':'Arts','languages':['en'],'evidence':{'age':'ages 8–12','languages':'English','accessibility':'step-free access'}}
    def response(self,data=None):return BytesIO(json.dumps({'stop_reason':'tool_use','content':[{'type':'tool_use','name':'activity_draft','input':data or self.output()}]}).encode())
    def post(self,brief=None,path='/demo/ai-draft/'):return self.client.post(path,json.dumps({'brief':self.brief if brief is None else brief}),content_type='application/json')
    @patch('community.activity_draft.urllib.request.urlopen')
    def test_structured_draft_returns_editable_fields_without_saving(self,send):
        send.return_value=self.response();before=Event.objects.count();r=self.post()
        self.assertEqual(r.status_code,200);self.assertEqual(r.json()['draft']['min_age'],8);self.assertEqual(r.json()['draft']['languages'],['en'])
        self.assertEqual(Event.objects.count(),before);self.assertNotContains(r,'test-server-secret')
        request=json.loads(send.call_args.args[0].data);self.assertEqual(request['messages'][0]['content'],self.brief)
        self.assertEqual(request['tool_choice']['name'],'activity_draft')
        self.assertNotIn(self.private.title,send.call_args.args[0].data.decode())
    @patch('community.activity_draft.urllib.request.urlopen')
    def test_unsubstantiated_access_age_and_language_are_not_filled(self,send):
        send.return_value=self.response();r=self.post('A drawing workshop.')
        self.assertEqual(r.status_code,200);draft=r.json()['draft']
        self.assertIsNone(draft['min_age']);self.assertEqual(draft['languages'],[]);self.assertEqual(draft['accessibility'],{'en':'','pt':''})
    @patch('community.activity_draft.urllib.request.urlopen')
    def test_forbidden_output_and_invalid_ages_fail_closed(self,send):
        for values in [{**self.output(),'price':15},{**self.output(),'min_age':13},{**self.output(),'languages':['invalid']}]:
            send.return_value=self.response(values);self.assertEqual(self.post().status_code,503)
    @override_settings(ANTHROPIC_API_KEY='')
    @patch('community.activity_draft.urllib.request.urlopen')
    def test_no_key_keeps_manual_editor_available(self,send):
        self.assertEqual(self.post().status_code,503);send.assert_not_called()
        self.assertEqual(self.client.get('/demo/creator/').status_code,200)
    @patch('community.activity_draft.urllib.request.urlopen')
    def test_input_post_and_csrf_validation(self,send):
        for brief in ['', 'x'*601]:self.assertEqual(self.post(brief).status_code,400)
        self.assertEqual(self.client.get('/demo/ai-draft/').status_code,405)
        self.assertEqual(Client(enforce_csrf_checks=True).post('/demo/ai-draft/',json.dumps({'brief':self.brief}),content_type='application/json').status_code,403)
        send.assert_not_called()
    @patch('community.activity_draft.urllib.request.urlopen')
    def test_live_endpoint_requires_verified_organizer_or_staff(self,send):
        self.assertEqual(self.post(path='/organizer/ai-draft/').status_code,302)
        self.client.force_login(self.parent);self.assertEqual(self.post(path='/organizer/ai-draft/').status_code,403)
        self.client.force_login(self.student);self.assertEqual(self.post(path='/organizer/ai-draft/').status_code,403)
        self.client.force_login(self.staff);send.return_value=self.response();self.assertEqual(self.post(path='/organizer/ai-draft/').status_code,200)
        organizer=User.objects.create_user('ai-organizer@test.invalid')
        member=Membership.objects.create(user=organizer,school=self.school,role='organizer',verified=False)
        self.client.force_login(organizer);self.assertEqual(self.post(path='/organizer/ai-draft/').status_code,403)
        member.verified=True;member.save();send.return_value=self.response()
        self.assertEqual(self.post(path='/organizer/ai-draft/').status_code,200)
    @patch('community.activity_draft.urllib.request.urlopen',side_effect=TimeoutError('test-server-secret'))
    def test_provider_error_never_exposes_credentials(self,send):
        response=self.post();self.assertEqual(response.status_code,503);self.assertNotContains(response,'test-server-secret',status_code=503)
