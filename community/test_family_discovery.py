"""Public discovery never widens school access or invents source facts."""
import json
from datetime import timedelta
from django.contrib.auth.models import AnonymousUser, User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from .models import School, Membership, Event, ActivitySession, SchoolProfile, ShortlistedSchool, SavedEvent, SaveReceipt
from .family_discovery import activity_results

class FamilyDiscoveryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff=User.objects.create_user('discovery-staff')
        cls.school=School.objects.create(name='Private school context',invite_code_hash='not-public')
        Membership.objects.create(user=cls.staff,school=cls.school,role='staff',verified=True)
        cls.parent=User.objects.create_user('discovery-parent')
        cls.other=User.objects.create_user('discovery-other')
        cls.day=timezone.now()+timedelta(days=10)
        common=dict(school=cls.school,created_by=cls.staff,published_by=cls.staff,status='published',visibility='public',description='Hands-on outdoor painting',venue='Garden studio',category='Arts',start_at=cls.day,end_at=cls.day+timedelta(hours=2),min_age=9,max_age=12,languages='en,pt',area='Estrela',activity_environment='outdoor',price_amount=0)
        cls.event=Event.objects.create(title='Garden painting test',**common)
        cls.private=Event.objects.create(title='Private painting test',**{**common,'visibility':'school'})
        cls.club=Event.objects.create(title='Recurring painting test',**{**common,'listing_type':'activity','start_at':timezone.now()-timedelta(days=20)})
        ActivitySession.objects.create(activity=cls.club,start_at=cls.day,end_at=cls.day+timedelta(hours=1))
        ActivitySession.objects.create(activity=cls.club,start_at=cls.day+timedelta(days=1),end_at=cls.day+timedelta(days=1,hours=1),is_cancelled=True)
        cls.profiles=[]
        for i in range(4):
            cls.profiles.append(SchoolProfile.objects.create(name=f'Sourced test school {i}',slug=f'test-school-{i}',city='Lisbon',school_type='international',min_age=6,max_age=12,stages='primary,lower_secondary',languages='en,pt',curriculum='Test curriculum',annual_fee_from=5000,fee_year='2026–27',fee_includes='Tuition only',source_name='Isolated test source',last_checked=timezone.now().date(),is_published=True))
        cls.draft=SchoolProfile.objects.create(name='Unpublished test school',slug='unpublished-school')
    def test_home_and_primary_destinations_are_public(self):
        response=self.client.get('/')
        self.assertContains(response,'Big discoveries for little explorers.')
        for path in ['/discover/activities/','/schools/','/saved/']:
            self.assertEqual(self.client.get(path).status_code,200)
        self.assertNotContains(response,self.private.title)
    def test_combined_activity_filters_and_recurring_dates(self):
        params={'age_group':'9-12','category':'Arts','area':'Estrela','price':'free','environment':'outdoor','language':'en','date_from':self.day.date().isoformat(),'date_to':self.day.date().isoformat()}
        form,events=activity_results(AnonymousUser(),params)
        self.assertTrue(form.is_valid());self.assertEqual({e.pk for e in events},{self.event.pk,self.club.pk})
        for key,value in [('age_group','3-5'),('category','Music'),('area','Porto'),('price','paid'),('environment','indoor'),('language','fr'),('max_price','-1')]:
            with self.subTest(key=key):self.assertEqual(activity_results(AnonymousUser(),{**params,key:value})[1],[])
        self.assertEqual(activity_results(AnonymousUser(),{**params,'date_from':'2030-01-02','date_to':'2030-01-01'})[1],[])
    def test_surprise_respects_filters_and_return_query(self):
        response=self.client.get('/discover/activities/',{'q':'Garden painting','age_group':'9-12','price':'free','surprise':'1'})
        self.assertEqual(response.status_code,302);self.assertTrue(response.url.startswith(f'/events/{self.event.pk}/?return_to='))
        detail=self.client.get(response.url);self.assertContains(detail,'Garden painting')
        self.assertContains(self.client.get('/discover/activities/?age_group=3-5&surprise=1'),'No published activities')
    def test_school_filters_only_supported_published_facts(self):
        response=self.client.get('/schools/',{'q':'Sourced test','age_group':'9-12','school_type':'international','stage':'primary','language':'en','curriculum':'Test curriculum','max_fee':'6000'})
        self.assertEqual(len(response.context['school_results']),4)
        self.assertNotContains(response,self.draft.name)
        self.assertEqual(len(self.client.get('/schools/?max_fee=4000').context['school_results']),0)
        self.assertEqual(self.client.get('/schools/unpublished-school/').status_code,404)
        self.assertContains(self.client.get('/schools/test-school-0/'),'Tuition only')
    def test_seed_is_explicitly_limited_to_project_source(self):
        school=SchoolProfile.objects.get(slug='unicorn-school-lisbon')
        self.assertEqual(school.school_type,'');self.assertIsNone(school.min_age);self.assertIsNone(school.annual_fee_from)
        self.assertIn('no independent',school.source_name)
        self.assertContains(self.client.get('/schools/unicorn-school-lisbon/'),'Not provided')
    def test_comparison_limit_and_missing_fields(self):
        query=[('school',p.slug) for p in self.profiles]
        from urllib.parse import urlencode
        self.assertEqual(self.client.get('/schools/compare/?'+urlencode(query)).status_code,400)
        response=self.client.get('/schools/compare/?'+urlencode(query[:3]))
        self.assertEqual(len(response.context['compare_profiles']),3);self.assertContains(response,'Not provided')
        self.assertNotContains(self.client.get('/schools/compare/?school=unpublished-school'),self.draft.name)
    def test_account_saves_are_idempotent_private_and_separate(self):
        self.client.force_login(self.parent)
        for _ in range(2):
            self.assertEqual(self.client.post('/discovery/saves/school/test-school-0/',json.dumps({'saved':True}),content_type='application/json').status_code,200)
        self.assertEqual(ShortlistedSchool.objects.filter(user=self.parent).count(),1)
        self.assertTrue(SaveReceipt.objects.filter(user=self.parent).exists())
        self.assertEqual(self.client.post(f'/discovery/saves/activity/{self.private.pk}/',json.dumps({'saved':True}),content_type='application/json').status_code,404)
        self.client.post(f'/discovery/saves/activity/{self.event.pk}/',json.dumps({'saved':True}),content_type='application/json')
        self.assertEqual(SavedEvent.objects.filter(user=self.parent).count(),1)
        self.client.force_login(self.other)
        self.assertFalse(self.client.get('/saved/').context['school_results'])
        self.assertEqual(self.client.post('/discovery/saves/school/test-school-0/',json.dumps({'saved':'yes'}),content_type='application/json').status_code,400)
    def test_guest_saved_fragment_revalidates_visibility(self):
        response=self.client.get('/discovery/saved/',{'activities':f'{self.event.pk},{self.private.pk}','schools':'test-school-0,unpublished-school'})
        self.assertContains(response,self.event.title);self.assertNotContains(response,self.private.title);self.assertNotContains(response,self.draft.name)
        self.assertEqual(response['Cache-Control'],'private, no-store')
    def test_school_staff_cannot_edit_unrelated_profile(self):
        self.client.force_login(self.parent);self.assertEqual(self.client.get('/staff/school-profile/').status_code,403)
        self.client.force_login(self.staff);response=self.client.get('/staff/school-profile/')
        self.assertEqual(response.status_code,200);self.assertEqual(response.context['form'].instance.school_id,self.school.pk)
    def test_publication_and_fees_need_sources(self):
        profile=SchoolProfile(name='Incomplete',slug='incomplete',is_published=True)
        with self.assertRaises(ValidationError):profile.full_clean()
        profile.is_published=False;profile.annual_fee_from=2000
        with self.assertRaises(ValidationError):profile.full_clean()
    def test_back_links_ignore_external_redirects(self):
        response=self.client.get('/schools/test-school-0/?return_to=https://example.com/')
        self.assertEqual(response.context['school_back'],'/schools/')
        self.assertEqual(self.client.get('/schools/test-school-0/',{'return_to':'http://['}).status_code,200)
        self.assertEqual(self.client.get(f'/events/{self.event.pk}/',{'return_to':'http://['}).status_code,200)
        response=self.client.get(f'/events/{self.event.pk}/?return_to=https://example.com/')
        self.assertNotEqual(response.context.get('discovery_return'),'https://example.com/')
