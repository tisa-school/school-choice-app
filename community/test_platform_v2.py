from datetime import timedelta
from io import BytesIO
import tempfile
from PIL import Image
from django.test import TestCase,Client,override_settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from .models import *

@override_settings(MEDIA_ROOT=tempfile.gettempdir()+'/tk-platform-v2-tests')
class PlatformV2Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school=School.objects.create(name='Unicorn School',invite_code_hash='private')
        cls.admin=User.objects.create_user('school-admin',email='admin@platform.test',password='IsolatedPlatform!729')
        Membership.objects.create(user=cls.admin,school=cls.school,role='staff',verified=True)
        cls.root=User.objects.create_user('platform-root',password='IsolatedPlatform!729',is_superuser=True,is_staff=True)
        cls.parent=User.objects.create_user('family-parent',password='IsolatedParent!729')
        cls.family=ParentAccount.objects.create(user=cls.parent)
        cls.child=ChildProfile.objects.create(parent=cls.family,nickname='Existing child',age_band='9-11')
        cls.other=User.objects.create_user('other-family',password='IsolatedParent!729');cls.other_family=ParentAccount.objects.create(user=cls.other)
        cls.event=Event.objects.create(school=cls.school,created_by=cls.admin,published_by=cls.admin,title='Football workshop test',description='Football skills',category='Sports',venue='Local pitch',area='Lisbon',start_at=timezone.now()+timedelta(days=4),status='published',visibility='public',min_age=8,max_age=12,languages='en',price_amount=0)
        cls.private=Event.objects.create(school=cls.school,created_by=cls.admin,title='Private football test',description='Private school content',category='Sports',venue='Private pitch',start_at=timezone.now()+timedelta(days=4),status='published',visibility='school')
        cls.experience=ExperienceListing.objects.create(title='Museum enquiry test',slug='museum-enquiry-test',created_by=cls.admin,school=cls.school,category='Museums & Culture',area='Lisbon',source_url='https://example.test/official',source_name='Isolated official test source',last_verified=timezone.now().date(),is_published=True,kind='appointment')
    def image(self):
        out=BytesIO();Image.new('RGB',(100,100),'purple').save(out,'PNG');return SimpleUploadedFile('photo.png',out.getvalue(),content_type='image/png')
    def test_five_primary_sections_and_no_prototype_tools(self):
        response=self.client.get('/');self.assertEqual(response.status_code,200)
        items=response.context['unified_navigation'];self.assertEqual([x['label'] for x in items],['Discover','Activities','Schools','My Family','Community'])
        self.assertNotIn('demo-catalogue',[x['key'] for x in items]);self.assertContains(response,'Discover more for your family in Lisbon.')
        self.assertContains(response,'What would you like to discover?');self.assertContains(response,'/help/')
    def test_account_menu_dashboard_is_permission_scoped(self):
        self.assertNotContains(self.client.get('/'),'href="/manage/"')
        self.client.force_login(self.parent);self.assertNotContains(self.client.get('/'),'href="/manage/"')
        self.client.force_login(self.admin);self.assertContains(self.client.get('/'),'Administrator Dashboard')
    def test_global_search_is_scoped_and_returns_actual_records(self):
        response=self.client.get('/search/?q=football');self.assertContains(response,self.event.title);self.assertNotContains(response,self.private.title)
        self.assertContains(self.client.get('/search/?q=museum'),'Museum enquiry test')
        self.assertNotContains(self.client.get('/search/?q=museum&date_from=2030-01-01'),'Museum enquiry test')
        self.assertNotContains(self.client.get('/search/?q=football&age_group=3-5'),self.event.title)
    def test_home_interest_group_filters_real_categories(self):
        response=self.client.get('/discover/activities/?theme=sports');self.assertContains(response,self.event.title)
        self.assertNotContains(self.client.get('/discover/activities/?theme=music'),self.event.title)
    def test_experience_has_no_invented_schedule_or_price(self):
        response=self.client.get('/experiences/museum-enquiry-test/');self.assertEqual(response.status_code,200)
        self.assertContains(response,'Enquiry Required');self.assertContains(response,'Price not confirmed');self.assertContains(response,'https://example.test/official')
    def test_experience_saving_is_persistent_and_owner_only(self):
        self.client.force_login(self.parent)
        response=self.client.post(f'/discovery/saves/experience/{self.experience.pk}/',{'saved':True},content_type='application/json');self.assertEqual(response.status_code,200)
        self.assertContains(self.client.get('/saved/'),self.experience.title)
        self.client.force_login(self.other);self.assertNotContains(self.client.get('/saved/'),self.experience.title)
    def test_private_calendar_create_edit_export_and_duplicate_prevention(self):
        self.client.force_login(self.parent);start=timezone.now()+timedelta(days=3);end=start+timedelta(hours=2)
        data={'title':'Private family picnic','start_at':start.strftime('%Y-%m-%dT%H:%M'),'end_at':end.strftime('%Y-%m-%dT%H:%M'),'note':'A plan, not a booking'}
        self.assertEqual(self.client.post('/family/private-events/new/',data).status_code,302)
        self.assertIn('Private calendar entry saved',SaveReceipt.objects.get(user=self.parent).action)
        self.assertEqual(self.client.post('/family/private-events/new/',data).status_code,200);self.assertEqual(PrivateFamilyEvent.objects.count(),1)
        item=PrivateFamilyEvent.objects.get();data['title']='Updated private family plan';self.client.post(f'/family/private-events/{item.pk}/',data)
        self.assertContains(self.client.get('/family/calendar/'),data['title'])
        self.assertContains(self.client.get('/family/calendar.ics'),data['title']);self.assertContains(self.client.get('/family/calendar.ics'),'DTEND:')
        self.client.force_login(self.other);self.assertEqual(self.client.get(f'/family/private-events/{item.pk}/').status_code,404)
        self.assertNotContains(self.client.get('/family/calendar.ics'),data['title'])
    def test_child_photos_remain_private_across_sign_in(self):
        self.client.force_login(self.parent)
        data={'nickname':self.child.nickname,'age_band':'9-11','interests':'Art','languages':'en','photo':self.image(),'photo_permission':'on'}
        self.assertEqual(self.client.post(f'/family/children/{self.child.pk}/',data).status_code,302)
        self.child.refresh_from_db();self.assertTrue(self.child.photo)
        url=f'/private/children/{self.child.pk}/photo/';self.assertEqual(self.client.get(url).status_code,200)
        self.client.force_login(self.other);self.assertEqual(self.client.get(url).status_code,404)
        self.client.logout();self.assertEqual(self.client.get(url).status_code,302)
        self.client.login(username=self.parent.username,password='IsolatedParent!729');self.assertEqual(self.client.get(url).status_code,200)
    def test_public_school_media_requires_permission_and_published_profile(self):
        profile=SchoolProfile.objects.get(slug='unicorn-school-lisbon')
        photo=SchoolMedia.objects.create(school_profile=profile,image=self.image(),description='Isolated campus test photo',credit='Test photographer',permission_confirmed=False,uploaded_by=self.admin)
        self.assertEqual(self.client.get(f'/schools/media/{photo.pk}/').status_code,404)
        photo.permission_confirmed=True;photo.includes_children=True;photo.save();self.assertEqual(self.client.get(f'/schools/media/{photo.pk}/').status_code,404)
        photo.guardian_consent=True;photo.save();self.assertEqual(self.client.get(f'/schools/media/{photo.pk}/').status_code,200)
    def test_research_queue_drafts_are_not_public_or_automatically_verified(self):
        self.client.force_login(self.root)
        response=self.client.post('/manage/research/',{'key':'united-lisbon'});self.assertEqual(response.status_code,302)
        profile=SchoolProfile.objects.get(name='United Lisbon International School');self.assertFalse(profile.is_published);self.assertIsNone(profile.last_checked)
        self.client.post('/manage/research/',{'key':'united-lisbon'});self.assertEqual(SchoolProfile.objects.filter(name=profile.name).count(),1)
        self.client.logout();self.assertNotContains(self.client.get('/schools/'),profile.name)
    def test_tour_get_creates_no_business_records_and_admin_tour_is_protected(self):
        models=[User,SchoolProfile,Event,ParentAccount,ChildProfile,SavedEvent,SavedExperience,PrivateFamilyEvent,PlatformAudit]
        before=[model.objects.count() for model in models]
        self.assertContains(self.client.get('/tour/'),'Interactive Product Tour');self.assertEqual(self.client.get('/manage/tour/').status_code,403)
        self.assertEqual(before,[model.objects.count() for model in models])
        self.client.force_login(self.admin);self.assertEqual(self.client.get('/manage/tour/').status_code,200)
    def test_manage_unpublish_and_audit_and_csrf(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(f'/manage/records/activities/{self.event.pk}/action/',{'action':'unpublish'}).status_code,302)
        self.event.refresh_from_db();self.assertEqual(self.event.status,'draft');self.assertTrue(PlatformAudit.objects.filter(action='content.unpublish').exists())
        self.client.logout();self.assertEqual(self.client.get(f'/events/{self.event.pk}/').status_code,404)
        client=Client(enforce_csrf_checks=True);client.force_login(self.admin)
        self.assertEqual(client.post(f'/manage/records/activities/{self.event.pk}/action/',{'action':'publish'}).status_code,403)
    def test_help_and_policy_pages_resolve(self):
        for path in ['/help/','/privacy/','/terms/','/safety/','/my-family/','/search/']:
            self.assertEqual(self.client.get(path).status_code,200,path)
    def test_site_default_language_is_used(self):
        SiteConfiguration.objects.create(default_language='pt-PT')
        response=Client().get('/help/');self.assertEqual(response['Content-Language'],'pt-PT')
    def test_readiness_and_administrator_diagnostics_do_not_expose_secrets(self):
        response=self.client.get('/health/');self.assertEqual(response.status_code,200);self.assertEqual(response.json(),{'status':'ok'})
        self.assertEqual(self.client.get('/manage/diagnostics/').status_code,302)
        self.client.force_login(self.parent);self.assertEqual(self.client.get('/manage/diagnostics/').status_code,403)
        self.client.force_login(self.admin)
        response=self.client.get('/manage/diagnostics/');self.assertEqual(response.status_code,200)
        from django.conf import settings
        self.assertNotContains(response,settings.SECRET_KEY)
        self.assertContains(response,'Not configured for actual email delivery')
    def test_administrator_create_school_and_event_publish_unpublish_archive(self):
        self.client.force_login(self.root)
        school_data={'name':'New sourced test school','city':'Lisbon','school_type':'international','min_age':6,'max_age':16,'languages':'en,pt','stages':['primary'],'source_name':'Isolated official source','source_url':'https://example.test/school','last_checked':timezone.now().date().isoformat(),'is_published':'on'}
        response=self.client.post('/manage/records/schools/new/',school_data);self.assertEqual(response.status_code,302)
        profile=SchoolProfile.objects.get(name=school_data['name']);self.assertTrue(profile.is_published)
        self.client.post(f'/manage/records/schools/{profile.pk}/action/',{'action':'archive'});profile.refresh_from_db();self.assertTrue(profile.archived);self.assertFalse(profile.is_published)
        self.client.post(f'/manage/records/schools/{profile.pk}/action/',{'action':'publish'});profile.refresh_from_db();self.assertFalse(profile.archived);self.assertTrue(profile.is_published)
        start=timezone.now()+timedelta(days=5)
        event_data={'school':self.school.pk,'title':'New administrator event','listing_type':'event','visibility':'public','category':'Sports','start_at':start.strftime('%Y-%m-%dT%H:%M'),'end_at':(start+timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M'),'venue':'Test venue','description':'Isolated source information','time_zone':'Europe/Lisbon','status':'published','min_age':8,'max_age':12,'languages':'en','activity_environment':'outdoor'}
        response=self.client.post('/manage/records/activities/new/',event_data);self.assertEqual(response.status_code,302)
        event=Event.objects.get(title=event_data['title']);self.assertEqual(event.published_by_id,self.root.pk)
        self.client.post(f'/manage/records/activities/{event.pk}/action/',{'action':'unpublish'});event.refresh_from_db();self.assertEqual(event.status,'draft')
        self.assertTrue(PlatformAudit.objects.filter(entity_id=str(event.pk),action='content.unpublish').exists())
    def test_super_administrator_can_review_reports_and_organisers_without_fake_school_membership(self):
        self.client.force_login(self.root)
        report=Feedback.objects.create(kind='report',message='Isolated report',school=self.school)
        response=self.client.post(f'/manage/review/reports/{report.pk}/',{'status':'resolved','review_note':'Isolated review'})
        self.assertEqual(response.status_code,302);report.refresh_from_db();self.assertEqual(report.reviewed_by_id,self.root.pk)
        candidate=User.objects.create_user('organiser-candidate')
        application=OrganizerApplication.objects.create(user=candidate,school=self.school,organization='Isolated organiser',contact_name='Test Contact',phone='12345678',description='Isolated test application')
        response=self.client.post(f'/manage/review/organisers/{application.pk}/',{'status':'approved','note':'Isolated review'})
        self.assertEqual(response.status_code,302);self.assertTrue(Membership.objects.filter(user=candidate,role='organizer',verified=True).exists())
    def test_authorised_tour_does_not_publish_due_announcements_or_save_preferences(self):
        from .models import Announcement,InterfacePreference
        announcement=Announcement.objects.create(school=self.school,author=self.admin,title='Scheduled test notice',body='Isolated scheduled content',status='scheduled',scheduled_for=timezone.now()-timedelta(minutes=1))
        self.client.force_login(self.admin)
        before=(PlatformAudit.objects.count(),InterfacePreference.objects.count())
        response=self.client.get('/manage/tour/');self.assertEqual(response.status_code,200)
        announcement.refresh_from_db();self.assertEqual(announcement.status,'scheduled')
        self.assertEqual(before,(PlatformAudit.objects.count(),InterfacePreference.objects.count()))
        self.assertEqual(self.client.post('/tour/',{'action':'save'}).status_code,405)

    def test_activity_with_private_family_plan_cannot_be_deleted(self):
        self.client.force_login(self.admin)
        self.event.status='draft';self.event.save(update_fields=['status'])
        FamilyPlan.objects.create(parent=self.family,event=self.event)
        self.client.post(f'/manage/records/activities/{self.event.pk}/action/',{'action':'delete','confirm':self.event.title})
        self.assertTrue(Event.objects.filter(pk=self.event.pk).exists())
        self.assertEqual(FamilyPlan.objects.filter(event=self.event).count(),1)
    def test_experience_source_disallows_credentials_and_non_web_schemes(self):
        from django.core.exceptions import ValidationError
        for source in ['ftp://example.test/source','https://name:password@example.test/source']:
            self.experience.source_url=source
            with self.assertRaises(ValidationError):self.experience.full_clean()
