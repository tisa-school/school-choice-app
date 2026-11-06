import json
from datetime import timedelta
from io import StringIO
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase,Client
from django.utils import timezone,translation
from . import test_features as fixtures
from .models import Event,Feedback,Membership,CATEGORIES
from .forms import EventForm
from .localization import catalog,ACTIVE_LOCALES

class WebSummitReleaseTests(TestCase):
    @classmethod
    def setUpTestData(cls): fixtures.FeatureTests.setUpTestData.__func__(cls)
    def test_about_and_feedback_pages_public_without_registration(self):
        for url in ['/about/','/feedback/','/feedback/received/','/calendar/','/demo/calendar/']:
            with self.subTest(url=url): self.assertEqual(self.client.get(url).status_code,200)
    def test_about_story_is_accurate_and_milestone_remains_planned(self):
        response=self.client.get('/about/')
        self.assertContains(response,'Small Ideas. Big Connections.')
        self.assertContains(response,'16 October 2026')
        self.assertContains(response,'12 November 2026')
        self.assertContains(response,'Planned milestone')
        self.assertContains(response,'without claiming a commercial partnership')
        self.assertContains(response,'Unicorn School')
    def test_public_contributor_cards_follow_approved_content_config(self):
        response=self.client.get('/about/')
        data=json.loads((settings.BASE_DIR/'content/project.json').read_text())
        students=[p for p in data['contributors'] if p['group']=='students']
        self.assertEqual(len(students),3)
        for person in students:
            self.assertContains(response,person['public_name'].split()[0])
        self.assertNotContains(response,'<img')
    def test_english_portuguese_and_turkish_core_content(self):
        for locale,title in [('en','Small Ideas. Big Connections.'),('pt-PT','Pequenas Ideias. Grandes Ligações.'),('tr','Küçük Fikirler. Büyük Bağlar.')]:
            with self.subTest(locale=locale):
                response=self.client.get('/about/',{'lang':locale})
                self.assertContains(response,title)
                self.assertContains(response,f'lang="{locale}"')
                self.assertEqual(response['Content-Language'],locale)
    def test_language_preference_persists_and_fallback_is_honest(self):
        self.client.get('/about/?lang=pt-PT')
        self.assertContains(self.client.get('/demo/'),'Sobre nós')
        response=Client().get('/about/?lang=he')
        self.assertEqual(response['Content-Language'],'en')
        self.assertEqual(response['Content-Language'],'en')
        self.assertNotIn('he',ACTIVE_LOCALES)
    def test_active_catalogs_have_equal_nonempty_coverage(self):
        en=catalog('en')
        self.assertGreater(len(en),200)
        for locale in ['pt-PT','tr']:
            translated=catalog(locale)
            self.assertEqual(set(en),set(translated))
            self.assertTrue(all(isinstance(value,str) and value.strip() for value in translated.values()))
            for key in ['Home','About Us','Send feedback','Gaming','Shopping','Theater & Drama']:
                self.assertNotEqual(translated[key],key)
    def test_translated_forms_keep_stable_category_values(self):
        with translation.override('tr'):
            form=EventForm()
            choices=dict(form.fields['category'].choices)
            self.assertEqual(choices['Gaming'],'Oyun ve turnuvalar')
            self.assertEqual(choices['Theater & Drama'],'Tiyatro ve drama')
    def test_old_and_new_categories_coexist_in_filters_and_forms(self):
        values=dict(CATEGORIES)
        for category in ['Sports','Music','Arts','School Life','Science','Nature','Coding','Games','Gaming','Shopping','Theater & Drama']:
            self.assertIn(category,values)
        for category in ['Gaming','Shopping','Theater & Drama']:
            event=Event.objects.create(school=self.school,created_by=self.staff,published_by=self.staff,title='New '+category,category=category,description='Test',venue='Test',start_at=timezone.now()+timedelta(days=2),visibility='public',status='published')
            from django.utils.html import escape
            self.assertContains(self.client.get('/events/',{'category':category}),escape(event.title))
    def test_environment_and_availability_filters_use_real_allocations(self):
        self.event.activity_environment='outdoor';self.event.capacity=1;self.event.save()
        self.assertContains(self.client.get('/events/?environment=outdoor&available=1'),self.event.title)
        self.assertNotContains(self.client.get('/events/?environment=indoor'),self.event.title)
        from .models import TicketRequest
        TicketRequest.objects.create(event=self.event,student=self.student,status='approved')
        self.assertNotContains(self.client.get('/events/?available=1'),self.event.title)
    def test_calendar_hides_private_and_cancelled_listings(self):
        month=timezone.localtime(self.event.start_at).strftime('%Y-%m')
        response=self.client.get('/calendar/',{'month':month})
        self.assertContains(response,self.event.title)
        self.assertNotContains(response,self.private.title)
        self.event.is_cancelled=True;self.event.save()
        self.assertNotContains(self.client.get('/calendar/',{'month':month}),self.event.title)
    def test_feedback_is_persisted_without_email_or_account(self):
        response=self.client.post('/feedback/',{'kind':'suggestion','message':'Please include more nature activities.','consent':'on'})
        self.assertEqual(response.status_code,302)
        row=Feedback.objects.get()
        self.assertIsNone(row.submitted_by);self.assertEqual(row.status,'new')
        self.assertContains(self.client.get('/feedback/received/'),'no email is sent')
    def test_feedback_requires_consent_and_rejects_honeypot(self):
        for data in [{'kind':'feedback','message':'Test'},{'kind':'feedback','message':'Test','consent':'on','website':'bot.example'}]:
            self.assertEqual(self.client.post('/feedback/',data).status_code,200)
        self.assertEqual(Feedback.objects.count(),0)
    def test_private_listing_cannot_be_reported_by_guessing_its_id(self):
        self.assertEqual(self.client.get(f'/feedback/?listing={self.private.pk}').status_code,404)
        self.client.post('/feedback/',{'kind':'report','listing':self.private.pk,'message':'Guess','consent':'on'})
        self.assertFalse(Feedback.objects.exists())
    def test_listing_report_is_scoped_to_school_reviewers(self):
        self.client.post('/feedback/',{'kind':'report','listing':self.event.pk,'message':'Please check this listing.','consent':'on'})
        row=Feedback.objects.get();self.assertEqual(row.school,self.school)
        self.client.force_login(self.staff)
        self.assertContains(self.client.get('/staff/feedback/'),'Please check this listing.')
        self.client.post(f'/staff/feedback/{row.pk}/',{'status':'resolved','note':'Checked with organizer'})
        row.refresh_from_db();self.assertEqual(row.status,'resolved');self.assertEqual(row.reviewed_by,self.staff)
        self.client.force_login(self.parent)
        self.assertEqual(self.client.get('/staff/feedback/').status_code,403)
    def test_other_school_staff_cannot_read_or_review_a_report(self):
        from .models import School
        school=School.objects.create(name='Different school',invite_code_hash='test-only')
        user=User.objects.create_user('different-staff');Membership.objects.create(user=user,school=school,role='staff',verified=True)
        row=Feedback.objects.create(kind='report',listing=self.event,school=self.school,message='Private report text')
        self.client.force_login(user)
        self.assertNotContains(self.client.get('/staff/feedback/'),'Private report text')
        self.assertEqual(self.client.post(f'/staff/feedback/{row.pk}/',{'status':'resolved'}).status_code,404)
    def test_feedback_not_public_and_user_text_is_escaped(self):
        row=Feedback.objects.create(kind='feedback',message='<script>alert(1)</script>')
        self.assertNotContains(self.client.get('/feedback/'),'<script>alert(1)</script>')
        self.assertNotContains(self.client.get('/about/'),'<script>alert(1)</script>')
    def test_feedback_submission_requires_csrf(self):
        client=Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/feedback/',{'kind':'feedback','message':'Test','consent':'on'}).status_code,403)
    def test_retention_command_is_dry_run_unless_explicitly_applied(self):
        row=Feedback.objects.create(kind='feedback',message='Old anonymous feedback')
        Feedback.objects.filter(pk=row.pk).update(created_at=timezone.now()-timedelta(days=100))
        call_command('prune_feedback',stdout=StringIO());self.assertTrue(Feedback.objects.filter(pk=row.pk).exists())
        call_command('prune_feedback',apply=True,stdout=StringIO());self.assertFalse(Feedback.objects.filter(pk=row.pk).exists())
