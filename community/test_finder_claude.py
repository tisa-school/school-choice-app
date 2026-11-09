import json
from io import BytesIO
from datetime import datetime,timezone as dt_timezone
from unittest.mock import patch
from urllib.error import HTTPError,URLError
from django.test import SimpleTestCase,override_settings
from .finder import interpret,validate_filters,FinderUnavailable

@override_settings(ANTHROPIC_API_KEY='test-only-secret',ANTHROPIC_MODEL='claude-haiku-4-5-20251001')
class ClaudeFinderTests(SimpleTestCase):
    def filters(self):return dict(category='Arts',age=11,language='en',area='',day='2026-11-14',price='',period='afternoon')
    def response(self,filters=None,**extra):
        data={'stop_reason':'tool_use','content':[{'type':'tool_use','name':'activity_filters','input':self.filters() if filters is None else filters}]}
        data.update(extra)
        return BytesIO(json.dumps(data).encode())
    @patch('community.finder.urllib.request.urlopen')
    @patch('community.finder.timezone.now',return_value=datetime(2026,11,9,tzinfo=dt_timezone.utc))
    def test_claude_messages_extracts_structured_filters(self,now,send):
        send.return_value=self.response()
        actual=interpret('English-friendly art activity for an 11-year-old on Saturday afternoon')
        self.assertEqual(actual['age'],'11');self.assertEqual(actual['day'],'2026-11-14');self.assertEqual(actual['period'],'afternoon')
        req=send.call_args.args[0];payload=json.loads(req.data)
        self.assertEqual(req.full_url,'https://api.anthropic.com/v1/messages')
        self.assertEqual(req.get_header('X-api-key'),'test-only-secret')
        self.assertEqual(req.get_header('Anthropic-version'),'2023-06-01')
        self.assertEqual(payload['model'],'claude-haiku-4-5-20251001')
        self.assertIn('2026-11-09 (Monday)',payload['system'])
        self.assertEqual(payload['tool_choice'],{'type':'tool','name':'activity_filters'})
        self.assertEqual(send.call_args.kwargs['timeout'],12)
        self.assertNotIn('test-only-secret',req.data.decode())
    @override_settings(ANTHROPIC_API_KEY='')
    @patch('community.finder.urllib.request.urlopen')
    def test_missing_key_is_explicit_without_network(self,send):
        with self.assertRaisesMessage(FinderUnavailable,'ANTHROPIC_API_KEY is missing'):interpret('Art')
        send.assert_not_called()
    @patch('community.finder.urllib.request.urlopen')
    def test_provider_errors_never_leak_secret_or_body(self,send):
        for error in [HTTPError('https://api.anthropic.com',401,'test-only-secret',{},None),URLError('test-only-secret'),TimeoutError('test-only-secret')]:
            send.side_effect=error
            with self.assertRaises(FinderUnavailable) as caught:interpret('Art')
            self.assertNotIn('test-only-secret',str(caught.exception))
            self.assertIn('temporarily unavailable',str(caught.exception))
    @patch('community.finder.urllib.request.urlopen')
    def test_invalid_or_incomplete_output_fails_closed(self,send):
        for response in [self.response({**self.filters(),'age':500}),self.response({},stop_reason='end_turn'),self.response({**self.filters(),'day':'2026-02-30'}),self.response({**self.filters(),'age':True}),self.response({**self.filters(),'event_id':999}),self.response({**self.filters(),'area':'x'*101}),BytesIO(b'not JSON')]:
            send.return_value=response
            with self.subTest(response=response):
                with self.assertRaises(FinderUnavailable):interpret('Art')
    def test_validator_rejects_impossible_dates(self):
        for day in ['2026-02-30','tomorrow','20261114']:
            with self.assertRaises(ValueError):validate_filters({**self.filters(),'day':day})

from django.test import TestCase
from .test_features import FeatureTests
from .finder import recommendations

@override_settings(ANTHROPIC_API_KEY='server-only-test-secret')
class ClaudeFinderPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):FeatureTests.setUpTestData.__func__(cls)
    @patch('community.finder.urllib.request.urlopen')
    def test_full_search_uses_claude_then_authorized_database_results(self,send):
        data=dict(category='Arts',age=11,language='en',area='',day='',price='free',period='')
        send.return_value=BytesIO(json.dumps({'stop_reason':'tool_use','content':[{'type':'tool_use','name':'activity_filters','input':data}]}).encode())
        response=self.client.post('/finder/',{'preferences':'English art for age 11, free','consent':'on'})
        self.assertEqual(response.status_code,200)
        self.assertContains(response,self.event.title)
        self.assertNotContains(response,self.private.title)
        self.assertContains(response,'class="match-reason"')
        self.assertContains(response,'Listed as free')
        self.assertNotContains(response,'server-only-test-secret')
        request=json.loads(send.call_args.args[0].data)
        self.assertEqual(request['messages'][0]['content'],'English art for age 11, free')
        self.assertNotIn(self.private.title,send.call_args.args[0].data.decode())
        self.assertTrue(response.context['ai_configured'])
    @override_settings(ANTHROPIC_API_KEY='')
    @patch('community.finder.urllib.request.urlopen')
    def test_missing_key_page_is_clear_and_submit_is_disabled(self,send):
        response=self.client.get('/finder/')
        self.assertContains(response,'ANTHROPIC_API_KEY')
        self.assertContains(response,'role="alert"')
        self.assertContains(response,'disabled')
        send.assert_not_called()
    def test_match_reason_is_one_sentence_from_actual_listing_data(self):
        rows=recommendations(self.parent,dict(category='Arts',age='11',language='en',price='free'))
        row=next(row for row in rows if row['event']==self.event)
        self.assertTrue(row['reason'].endswith('.'))
        self.assertEqual(row['reason'].count('.'),1)
        self.assertIn('Published ages 8–14',row['reason'])
        self.assertIn('Listed as free',row['reason'])
