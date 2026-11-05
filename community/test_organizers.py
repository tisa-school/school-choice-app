from datetime import timedelta
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from .models import *
from . import test_features as feature_fixtures
from .services import express_interest,parent_decision,confirm_participation,decide
from .organizers import cancel_listing

class OrganizerStudioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        feature_fixtures.FeatureTests.setUpTestData.__func__(cls)
        cls.organizer=User.objects.create_user('event-organizer',password='OrganizerTesting!983')
        cls.organizer_member=Membership.objects.create(user=cls.organizer,school=cls.school,role='organizer',verified=True)
        cls.another=User.objects.create_user('another-organizer',password='OrganizerTesting!983')
        cls.another_member=Membership.objects.create(user=cls.another,school=cls.school,role='organizer',verified=True)
        cls.listing=Event.objects.create(school=cls.school,created_by=cls.organizer,published_by=cls.staff,title='Organizer test event',category='Arts',description='Test event details',venue='Test hall',start_at=timezone.now()+timedelta(days=5),end_at=timezone.now()+timedelta(days=5,hours=2),capacity=2,min_age=8,max_age=14,status='published',visibility='public')
    def setUp(self): self.client.force_login(self.organizer)
    def payload(self,**changes):
        data={'title':'New organizer listing','category':'Arts','start_at':(timezone.now()+timedelta(days=5)).strftime('%Y-%m-%dT%H:%M'),'end_at':(timezone.now()+timedelta(days=5,hours=2)).strftime('%Y-%m-%dT%H:%M'),'venue':'Test hall','description':'Test details','min_age':8,'max_age':14}
        data.update(changes);return data
    def approved_interest(self,child=None):
        child=child or self.child
        owner=child.parent.user
        item=express_interest(owner,self.listing.pk,child.pk)
        parent_decision(owner,item.pk,'send')
        parent_decision(owner,item.pk,'approve','FamilyTesting!729')
        return item
    def test_dashboard_editor_manager_preview_render(self):
        for route in ['/organizer/','/organizer/new/',f'/organizer/{self.listing.pk}/',f'/organizer/events/{self.listing.pk}/',f'/organizer/events/{self.listing.pk}/?preview=1']:
            with self.subTest(route=route): self.assertEqual(self.client.get(route).status_code,200)
    def test_draft_can_be_incomplete_and_remains_private(self):
        self.client.post('/organizer/new/',{'title':'Incomplete private draft','category':'Arts','start_at':self.listing.start_at.strftime('%Y-%m-%dT%H:%M'),'action':'draft'})
        event=Event.objects.get(title='Incomplete private draft')
        self.assertEqual(event.status,'draft');self.assertEqual(event.venue,'')
        self.client.logout();self.assertEqual(self.client.get(f'/events/{event.pk}/').status_code,404)
    def test_submission_cannot_publish_or_verify_itself(self):
        self.client.post('/organizer/new/',self.payload(status='published',identity_verified='on',published_by=self.organizer.pk,visibility='public',action='submit'))
        event=Event.objects.get(title='New organizer listing')
        self.assertEqual(event.status,'submitted');self.assertIsNone(event.published_by);self.assertFalse(event.identity_verified)
    def test_submission_requires_future_date_and_valid_details(self):
        response=self.client.post('/organizer/new/',self.payload(start_at=(timezone.now()-timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),end_at='',contact_website='javascript:alert(1)',action='submit'))
        self.assertEqual(response.status_code,200);self.assertFalse(Event.objects.filter(title='New organizer listing').exists())
    def test_contact_details_are_hidden_until_explicitly_shared(self):
        self.listing.contact_name='Private business contact';self.listing.contact_phone='+351 210 123 456';self.listing.contact_website='https://example.org';self.listing.save()
        self.client.logout()
        self.assertNotContains(self.client.get(f'/events/{self.listing.pk}/'),'Private business contact')
        self.listing.contact_public=True;self.listing.save()
        response=self.client.get(f'/events/{self.listing.pk}/')
        self.assertContains(response,'Private business contact');self.assertContains(response,'tel:+351210123456')
    def test_address_map_link_is_escaped_and_venue_only(self):
        self.listing.address='Test venue, Lisbon & surroundings';self.listing.save()
        response=self.client.get(f'/events/{self.listing.pk}/')
        self.assertContains(response,'openstreetmap.org/search?query=')
        self.assertIn('Lisbon+%26+surroundings',self.listing.map_url)
    def test_public_contact_requires_contact_name_and_contact_method(self):
        self.client.post('/organizer/new/',self.payload(contact_public='on',contact_name='',contact_phone='',action='submit'))
        self.assertFalse(Event.objects.filter(title='New organizer listing').exists())
    def test_another_organizer_cannot_view_or_manage_roster(self):
        self.client.force_login(self.another)
        for route in [f'/organizer/{self.listing.pk}/',f'/organizer/events/{self.listing.pk}/']:
            self.assertEqual(self.client.get(route).status_code,404)
        self.assertEqual(self.client.post(f'/organizer/events/{self.listing.pk}/cancel/',{'note':'No access'}).status_code,404)
    def test_public_has_no_roster_or_private_preview_access(self):
        self.client.logout()
        self.assertEqual(self.client.get(f'/organizer/events/{self.listing.pk}/').status_code,302)
    def test_child_identities_hidden_before_parent_approval_including_decline(self):
        item=express_interest(self.parent,self.listing.pk,self.child.pk)
        parent_decision(self.parent,item.pk,'send');parent_decision(self.parent,item.pk,'decline','FamilyTesting!729')
        response=self.client.get(f'/organizer/events/{self.listing.pk}/')
        self.assertNotContains(response,'Test Child')
        self.assertNotContains(response,self.parent.username)
    def test_roster_shows_parent_approved_nickname_and_confirmed_status(self):
        item=self.approved_interest()
        response=self.client.get(f'/organizer/events/{self.listing.pk}/')
        self.assertContains(response,'Test Child');self.assertContains(response,'Awaiting organizer confirmation')
        self.assertNotContains(response,self.parent.username)
        self.client.post(f'/organizer/events/{self.listing.pk}/family/{item.pk}/decision/',{'status':'confirmed','note':'See you there'})
        item.refresh_from_db();self.assertEqual(item.status,'confirmed');self.assertEqual(item.reviewed_by,self.organizer)
        self.assertContains(self.client.get(f'/organizer/events/{self.listing.pk}/?status=confirmed'),'Test Child')
    def test_organizer_decisions_reject_other_owners_and_full_capacity(self):
        a=self.approved_interest();b=self.approved_interest(self.other_child)
        confirm_participation(self.organizer,self.organizer_member,a.pk,'confirmed')
        confirm_participation(self.organizer,self.organizer_member,b.pk,'confirmed')
        self.assertEqual(self.listing.remaining,0)
        ticket=TicketRequest.objects.create(event=self.listing,student=self.student)
        with self.assertRaises(ValueError): decide(self.organizer,self.organizer_member,ticket.pk,'approved')
        with self.assertRaises(PermissionError): confirm_participation(self.another,self.another_member,a.pk,'declined')
    def test_organizer_can_add_sessions_but_changes_require_review(self):
        self.listing.listing_type='activity';self.listing.save()
        self.client.post(f'/staff/activities/{self.listing.pk}/sessions/new/',{'start_at':self.listing.start_at.strftime('%Y-%m-%dT%H:%M'),'end_at':self.listing.end_at.strftime('%Y-%m-%dT%H:%M'),'capacity':5})
        self.assertEqual(self.listing.sessions.count(),1)
        self.listing.refresh_from_db();self.assertEqual(self.listing.status,'submitted');self.assertIsNone(self.listing.published_by)
    def test_cancellation_updates_all_requests_and_notifies_in_app(self):
        item=self.approved_interest();confirm_participation(self.organizer,self.organizer_member,item.pk,'confirmed')
        ticket=TicketRequest.objects.create(event=self.listing,student=self.student,status='approved')
        self.client.post(f'/organizer/events/{self.listing.pk}/cancel/',{'note':'Venue unavailable'})
        self.listing.refresh_from_db();item.refresh_from_db();ticket.refresh_from_db()
        self.assertTrue(self.listing.is_cancelled);self.assertEqual(item.status,'cancelled');self.assertEqual(ticket.status,'cancelled')
        self.assertTrue(Notification.objects.filter(user=self.parent,title='A listing you requested was cancelled').exists())
        self.client.logout();self.assertContains(self.client.get(f'/events/{self.listing.pk}/'),'Event cancelled.')
        self.assertNotContains(self.client.get('/events/'),'Organizer test event')
    def test_cancellation_requires_reason_and_cannot_be_reversed_by_edit(self):
        with self.assertRaises(ValueError): cancel_listing(self.organizer,self.organizer_member,self.listing.pk,'')
        cancel_listing(self.organizer,self.organizer_member,self.listing.pk,'Cancelled for testing')
        self.client.post(f'/organizer/{self.listing.pk}/',self.payload(action='submit'))
        self.listing.refresh_from_db();self.assertTrue(self.listing.is_cancelled)
    def test_adult_can_apply_without_gaining_organizer_role(self):
        adult=User.objects.create_user('applicant')
        self.client.force_login(adult)
        self.client.post('/organizer/apply/',{'school':self.school.pk,'organization':'Test activity company','contact_name':'Test adult','phone':'+351 210 123 456','website':'https://example.org','description':'Supervised activities','adult_consent':'on','status':'approved','role':'staff'})
        application=OrganizerApplication.objects.get(user=adult)
        self.assertEqual(application.status,'pending');self.assertFalse(Membership.objects.filter(user=adult).exists())
    def test_only_staff_of_reviewing_school_can_approve_application(self):
        adult=User.objects.create_user('pending-applicant')
        application=OrganizerApplication.objects.create(user=adult,school=self.school,organization='Test org',contact_name='Test',phone='12345678',description='Test')
        self.assertEqual(self.client.post(f'/staff/organizers/{application.pk}/',{'status':'approved'}).status_code,403)
        self.client.force_login(self.staff)
        self.client.post(f'/staff/organizers/{application.pk}/',{'status':'approved','note':'Access reviewed'})
        application.refresh_from_db();self.assertEqual(application.status,'approved');self.assertEqual(application.reviewed_by,self.staff)
        self.assertEqual(Membership.objects.get(user=adult).role,'organizer')
    def test_student_cannot_apply_as_adult_organizer(self):
        self.client.force_login(self.student)
        self.assertEqual(self.client.get('/organizer/apply/').status_code,403)

from django.test import override_settings
@override_settings(STORAGES={'default':{'BACKEND':'community.storage.DatabasePrivateStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class PrivateImageEditorTests(TestCase):
    def test_private_image_can_be_edited_without_public_storage_url_or_reupload(self):
        from . import test_features as feature_fixtures
        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image
        from io import BytesIO
        school=School.objects.create(name='Image test school',invite_code_hash='test-only')
        user=User.objects.create_user('image-owner')
        Membership.objects.create(user=user,school=school,role='organizer',verified=True)
        image=BytesIO();Image.new('RGB',(20,20),'white').save(image,format='PNG')
        event=Event.objects.create(school=school,created_by=user,title='Private image test',category='Arts',description='Details',venue='Hall',start_at=timezone.now()+timedelta(days=4),image=SimpleUploadedFile('test.png',image.getvalue(),content_type='image/png'))
        original=event.image.name;self.client.force_login(user)
        self.assertEqual(self.client.get(f'/organizer/{event.pk}/').status_code,200)
        self.client.post(f'/organizer/{event.pk}/',{'title':'Updated image title','category':'Arts','start_at':event.start_at.strftime('%Y-%m-%dT%H:%M'),'venue':'Hall','description':'Updated details','action':'submit'})
        event.refresh_from_db();self.assertEqual(event.title,'Updated image title');self.assertEqual(event.image.name,original)

class OrganizerTimezoneTests(TestCase):
    def test_posted_time_is_parsed_in_selected_listing_zone(self):
        from .forms import OrganizerSubmissionForm
        form=OrganizerSubmissionForm({'title':'Time zone test','category':'Arts','start_at':f'{timezone.now().year+1}-01-15T15:00','end_at':f'{timezone.now().year+1}-01-15T17:00','time_zone':'America/New_York','venue':'Test','description':'Details'})
        self.assertTrue(form.is_valid(),form.errors)
        from zoneinfo import ZoneInfo
        self.assertEqual(form.cleaned_data['start_at'].astimezone(ZoneInfo('UTC')).hour,20)

from django.test import TransactionTestCase
class OrganizerCancelRaceTests(TransactionTestCase):
    def test_cancellation_and_approval_serialize_without_overbooking_or_deadlock(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import close_old_connections
        school=School.objects.create(name='Cancellation race school',invite_code_hash='test-only')
        owner=User.objects.create_user('race-organizer')
        member=Membership.objects.create(user=owner,school=school,role='organizer',verified=True)
        student=User.objects.create_user('race-student')
        event=Event.objects.create(school=school,created_by=owner,title='Race event',category='Arts',description='Test',venue='Test',start_at=timezone.now()+timedelta(days=5),capacity=1,status='published')
        ticket=TicketRequest.objects.create(event=event,student=student)
        barrier=Barrier(2)
        def act(action):
            close_old_connections()
            try:
                actor=User.objects.get(pk=owner.pk);membership=Membership.objects.get(pk=member.pk)
                barrier.wait(timeout=10)
                if action=='cancel': cancel_listing(actor,membership,event.pk,'Test cancellation');return 'cancelled'
                try: decide(actor,membership,ticket.pk,'approved');return 'approved'
                except ValueError: return 'closed'
            finally: close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool: result=list(pool.map(act,['cancel','approve']))
        self.assertIn('cancelled',result)
        event.refresh_from_db();ticket.refresh_from_db()
        self.assertTrue(event.is_cancelled);self.assertEqual(ticket.status,'cancelled');self.assertEqual(event.remaining,1)

class OrganizerSchoolPrivacyTests(TestCase):
    @classmethod
    def setUpTestData(cls): feature_fixtures.FeatureTests.setUpTestData.__func__(cls)
    def test_external_posting_access_does_not_unlock_other_school_private_content(self):
        organizer=User.objects.create_user('privacy-organizer')
        Membership.objects.create(user=organizer,school=self.school,role='organizer',verified=True)
        Announcement.objects.create(school=self.school,author=self.staff,title='Private school note',body='Private details',status='published')
        self.client.force_login(organizer)
        self.assertNotContains(self.client.get('/'),'Private school test event')
        self.assertNotContains(self.client.get('/'),'Private school note')
        self.assertEqual(self.client.get(f'/events/{self.private.pk}/').status_code,404)
        self.assertEqual(self.client.get('/announcements/').status_code,403)
        from .services import notify_school
        note=Announcement.objects.get(title='Private school note')
        notify_school(note)
        self.assertFalse(Notification.objects.filter(user=organizer,title='Private school note').exists())

class OrganizerSignupRoutingTests(TestCase):
    def test_signup_preserves_internal_application_destination_but_rejects_external_redirect(self):
        data={'name':'Test organizer','email':'signup-organizer@example.test','password1':'UniqueOrganizer!785','password2':'UniqueOrganizer!785'}
        response=self.client.post('/accounts/signup/?next=/organizer/apply/',data)
        self.assertEqual(response.url,'/organizer/apply/')
        self.client.logout();data['email']='second-signup@example.test'
        response=self.client.post('/accounts/signup/?next=https://untrusted.example/',data)
        self.assertEqual(response.url,'/join/')
