import json
from datetime import datetime, timezone as dt_timezone
from unittest.mock import patch
from django.test import TestCase, Client
from . import test_features as fixtures
from .finder import FinderUnavailable


class AskTKTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.FeatureTests.setUpTestData.__func__(cls)

    def ask(self, **changes):
        data = dict(preferences='English art', consent=True, scope='live', mode='ai')
        data.update(changes)
        return self.client.post('/assistant/ask/', json.dumps(data), content_type='application/json')

    @patch('community.ask_tk.interpret', return_value={'category':'Arts','age':'11','language':'en'})
    def test_suggestions_are_authoritative_and_school_scoped(self, interpret):
        response = self.ask()
        self.assertEqual(response.status_code, 200)
        links = [item['url'] for item in response.json()['results']]
        self.assertIn(f'/events/{self.event.pk}/', links)
        self.assertNotIn(f'/events/{self.private.pk}/', links)
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.client.force_login(self.student)
        self.assertIn(f'/events/{self.private.pk}/', [item['url'] for item in self.ask().json()['results']])

    @patch('community.ask_tk.recommendations')
    @patch('community.ask_tk.interpret', return_value={'category':'Arts'})
    def test_demo_only_receives_filters_and_never_queries_live_catalogue(self, interpret, recommendations):
        response = self.ask(scope='demo')
        self.assertEqual(response.json()['results'], [])
        self.assertEqual(response.json()['filters'], {'category':'Arts'})
        recommendations.assert_not_called()
        interpret.assert_called_once_with('English art')
        self.assertEqual(self.ask(scope='demo', preferences='Art on 2026-11-14').status_code, 200)

    @patch('community.ask_tk.interpret')
    def test_browsing_needs_no_key_and_sends_nothing_to_ai(self, interpret):
        response = self.ask(mode='browse', preferences='', consent=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['source'], 'catalogue')
        self.assertTrue(response.json()['results'])
        interpret.assert_not_called()

    @patch('community.ask_tk.interpret')
    def test_consent_validation_and_contact_information_fail_before_provider(self, interpret):
        for changes in [dict(consent=False),dict(preferences=''),dict(preferences='x'*501),dict(preferences='email me at kid@example.com'),dict(preferences='call +351 912 345 678'),dict(scope='other'),dict(mode='browse')]:
            self.assertEqual(self.ask(**changes).status_code, 400)
        interpret.assert_not_called()
        self.assertEqual(self.client.get('/assistant/ask/').status_code, 405)
        self.assertEqual(Client(enforce_csrf_checks=True).post('/assistant/ask/', '{}', content_type='application/json').status_code, 403)

    @patch('community.ask_tk.interpret', side_effect=FinderUnavailable('private provider error'))
    def test_unavailable_has_safe_explicit_error(self, interpret):
        response = self.ask()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {'error':'unavailable'})
        self.assertEqual(response['Cache-Control'], 'no-store')

    @patch('community.ask_tk.timezone.now', return_value=datetime(2026,11,10,tzinfo=dt_timezone.utc))
    @patch('community.ask_tk.interpret', return_value={'day':'2026-11-14'})
    def test_weekend_is_saturday_and_sunday(self, interpret, now):
        response = self.ask(scope='demo', preferences='what can I do this weekend?')
        self.assertEqual(response.json()['days'], ['2026-11-14','2026-11-15'])
        self.assertEqual(response.json()['filters']['day'], '')

    def test_shared_templates_load_widget(self):
        for path in ['/demo/','/community/','/finder/','/about/','/accounts/login/']:
            self.assertContains(self.client.get(path), 'community/ask-tk.')
