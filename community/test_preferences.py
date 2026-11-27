import json
from datetime import timedelta
from pathlib import Path
from django.test import TestCase,Client
from django.contrib.auth.models import User
from django.utils import timezone,translation
from .models import School,Event,DiscoveryPreference,Membership,InterfacePreference,TicketRequest
from .preferences import recommendations_for
from .localization import ACTIVE_LOCALES,catalog

class DiscoveryPreferenceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner=User.objects.create_user('preference-test',password='TestPrefs!482')
        cls.school=School.objects.create(name='Fictional preference school')
        cls.event=Event.objects.create(school=cls.school,created_by=cls.owner,published_by=cls.owner,visibility='public',status='published',title='Fictional science workshop',description='Isolated fictional fixture.',category='Science',venue='Test venue',city='Lisbon',event_kind='workshop',attendance_mode='in_person',start_at=timezone.now()+timedelta(days=4),price_amount=0,capacity=10)
        cls.unknown=Event.objects.create(school=cls.school,created_by=cls.owner,published_by=cls.owner,visibility='public',status='published',title='Unknown price',description='Fixture',category='Science',venue='Test',start_at=timezone.now()+timedelta(days=3))
    def post_answers(self,**override):
        values={'language':'en','audience':'student','interests':['Science'],'event_kinds':['workshop'],'city':'Lisbon','attendance':'in_person','budget':'free'};values.update(override)
        return self.client.post('/onboarding/complete/',json.dumps(values),content_type='application/json')
    def test_first_visit_then_completed_and_skipped(self):
        self.assertContains(self.client.get('/'),'id="discovery-onboarding"')
        self.assertEqual(self.post_answers().status_code,200)
        response=self.client.get('/')
        self.assertNotContains(response,'id="discovery-onboarding"')
        self.assertEqual(response['Cache-Control'],'private, no-store')
        self.client=Client();self.assertEqual(self.client.post('/onboarding/complete/',json.dumps({'skip':True}),content_type='application/json').status_code,200)
        self.assertNotContains(self.client.get('/'),'id="discovery-onboarding"')
    def test_guest_saved_and_account_import_persists(self):
        self.post_answers();self.client.force_login(self.owner)
        self.client.get('/')
        self.assertEqual(DiscoveryPreference.objects.get(user=self.owner).answers['interests'],['Science'])
        self.client=Client();self.client.force_login(self.owner)
        self.assertNotContains(self.client.get('/'),'id="discovery-onboarding"')
    def test_audience_does_not_grant_roles(self):
        self.client.force_login(self.owner);self.post_answers(audience='teacher')
        self.assertFalse(Membership.objects.filter(user=self.owner).exists())
        self.assertEqual(self.client.get('/staff/').status_code,302)
        Membership.objects.create(user=self.owner,school=self.school,role='student',verified=True)
        self.post_answers(audience='teacher')
        self.assertEqual(Membership.objects.get(user=self.owner).role,'student')
        self.assertEqual(self.client.get('/staff/').status_code,403)
        self.assertEqual(self.post_answers(audience='admin').status_code,400)
    def test_csrf_required_and_invalid_input_not_saved(self):
        client=Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/onboarding/complete/','{"skip":true}',content_type='application/json').status_code,403)
        for values in [{'language':'invalid'},{'city':'x'*101},{'interests':['invalid']},{'completed':True},{'city':{}},{'interests':'Science'}]:
            self.assertEqual(self.post_answers(**values).status_code,400)
        self.assertNotIn('tk_discovery_preferences',self.client.session)
    def test_recommendations_only_real_visible_available_and_free(self):
        self.post_answers();response=self.client.get('/')
        matches=response.context['personalized_recommendations']
        self.assertEqual([x['event'].pk for x in matches],[self.event.pk]);self.assertIn('Matches your interests',matches[0]['reason'])
        self.event.is_cancelled=True;self.event.save()
        self.assertEqual(self.client.get('/').context['personalized_recommendations'],[])
    def test_private_unpublished_past_full_never_recommended(self):
        self.post_answers()
        for changes in [{'visibility':'school'},{'status':'draft'},{'start_at':timezone.now()-timedelta(days=1)},{'capacity':0}]:
            original={k:getattr(self.event,k) for k in changes}
            for k,v in changes.items():setattr(self.event,k,v)
            self.event.save();self.assertEqual(self.client.get('/').context['personalized_recommendations'],[])
            for k,v in original.items():setattr(self.event,k,v)
            self.event.save()
    def test_all_events_still_accessible(self):
        self.post_answers()
        self.assertContains(self.client.get('/discover/activities/'),'Unknown price')
    def test_all_languages_questions_and_switch_persist(self):
        keys=json.loads((Path(__file__).resolve().parent.parent/'content/onboarding-translation-keys.json').read_text())
        for locale in ACTIVE_LOCALES:
            with self.subTest(locale=locale):
                response=self.client.get('/?lang='+locale)
                self.assertEqual(response.status_code,200);self.assertEqual(response['Content-Language'],locale)
                self.assertContains(response,catalog(locale)['What language do you prefer?'])
                self.assertEqual(self.client.get('/schools/')['Content-Language'],locale)
                for key in keys:self.assertTrue(catalog(locale).get(key))
                self.assertEqual(set(catalog(locale)),set(catalog('en')))
    def test_explicit_url_language_overrides_saved_and_settings_post(self):
        self.client.force_login(self.owner);self.post_answers(language='fr')
        self.assertEqual(self.client.get('/?lang=pt')['Content-Language'],'pt-PT')
        self.assertEqual(InterfacePreference.objects.get(user=self.owner).language,'pt-PT')
        data={'language':'es','audience':'parent','interests':['Arts'],'event_kinds':['exhibition'],'city':'Cascais','attendance':'both','budget':'both'}
        response=self.client.post('/settings/preferences/?lang=en',data,follow=True)
        self.assertEqual(response.status_code,200);self.assertEqual(response['Content-Language'],'es')
        self.assertEqual(DiscoveryPreference.objects.get(user=self.owner).answers['city'],'Cascais')
        self.assertEqual(InterfacePreference.objects.get(user=self.owner).language,'es')
    def test_authored_event_translation_is_rendered_and_escaped(self):
        self.event.translations={'pt-PT':{'title':'Oficina de ciência fictícia','description':'Texto traduzido.'},'fr':{'title':'<script>alert(1)</script>'}}
        self.event.save()
        self.assertContains(self.client.get(f'/events/{self.event.pk}/?lang=pt-PT'),'Oficina de ciência fictícia')
        response=self.client.get(f'/events/{self.event.pk}/?lang=fr')
        self.assertNotContains(response,'<script>alert(1)</script>');self.assertContains(response,'&lt;script&gt;alert(1)&lt;/script&gt;')
    def test_self_closing_input_placeholder_localizes(self):
        from .html_localization import localize_html
        self.assertIn('placeholder="Pesquisar"',localize_html('<input placeholder="Search"/>',lambda x:'Pesquisar' if x=='Search' else x))
    def test_all_public_pages_render_in_every_supported_locale(self):
        public=['/','/schools/','/discover/activities/','/finder/','/saved/','/about/','/help/','/privacy/','/safety/','/settings/preferences/']
        for locale in ACTIVE_LOCALES:
            for url in public:
                with self.subTest(locale=locale,path=url):
                    response=self.client.get(url+'?lang='+locale)
                    self.assertEqual(response.status_code,200)
                    self.assertEqual(response['Content-Language'],locale)
                    self.assertContains(response,'dir="rtl"' if locale in ['ar','ur'] else 'dir="ltr"')
    def test_account_locale_survives_new_session_and_receipt_is_real(self):
        from .models import SaveReceipt
        self.client.force_login(self.owner)
        self.assertEqual(self.post_answers(language='pt-PT').status_code,200)
        self.assertTrue(SaveReceipt.objects.filter(user=self.owner).exists())
        self.client=Client();self.client.force_login(self.owner)
        self.assertEqual(self.client.get('/profile/')['Content-Language'],'pt-PT')
    def test_invalid_authored_translation_rejected_by_existing_form(self):
        from .forms import EventForm
        form=EventForm();form.cleaned_data={'translations':{'fr':{'unknown':'x'}}}
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):form.clean_translations()

    def test_localized_city_name_matches_same_real_location(self):
        self.post_answers(city='Lisboa',interests=[],event_kinds=[],attendance='both',budget='both')
        results=self.client.get('/').context['personalized_recommendations']
        self.assertEqual([x['event'].pk for x in results],[self.event.pk])
        self.assertEqual(results[0]['reason'],'Matches your preferred area')
