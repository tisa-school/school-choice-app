from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.test import TestCase, TransactionTestCase, Client, override_settings
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.db import IntegrityError, transaction, close_old_connections
from django.utils import timezone
from django.core import mail
from .models import *
from .services import request_ticket,decide,cancel,publish_due
from .forms import EventForm,AnnouncementForm

class SchoolWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school=School.objects.create(name='Test school',invite_code_hash=make_password('private-test-invite'))
        cls.other=School.objects.create(name='Other school',invite_code_hash=make_password('another-private-code'))
        cls.student=User.objects.create_user(username='student@example.com',email='student@example.com',password='TestPassword!482',first_name='Student')
        cls.student2=User.objects.create_user(username='second@example.com',email='second@example.com',password='TestPassword!482')
        cls.staff=User.objects.create_user(username='staff@example.com',password='TestPassword!482')
        cls.stranger=User.objects.create_user(username='stranger@example.com',password='TestPassword!482')
        cls.member=Membership.objects.create(user=cls.student,school=cls.school,verified=True)
        cls.member2=Membership.objects.create(user=cls.student2,school=cls.school,verified=True)
        cls.staff_member=Membership.objects.create(user=cls.staff,school=cls.school,role='staff',verified=True)
        Membership.objects.create(user=cls.stranger,school=cls.other,verified=True)
        cls.event=Event.objects.create(school=cls.school,created_by=cls.staff,title='Test rehearsal',category='Music',description='A private school event.',venue='Hall',start_at=timezone.now()+timedelta(days=5),capacity=1,status='published')
        cls.draft=Event.objects.create(school=cls.school,created_by=cls.staff,title='Unpublished draft',category='Arts',description='Draft',venue='Hall',start_at=timezone.now()+timedelta(days=6))
    def setUp(self): self.client.force_login(self.student)
    def test_student_pages_render(self):
        for url in ['/','/events/','/events/?q=rehearsal','/events/?category=Music','/events/?day=2026-11-03','/tickets/','/saved/','/announcements/','/notifications/','/profile/','/collections/new/',f'/events/{self.event.pk}/']:
            with self.subTest(url=url): self.assertEqual(self.client.get(url).status_code,200)
    def test_staff_pages_render(self):
        self.client.force_login(self.staff)
        for url in ['/staff/','/staff/events/new/',f'/staff/events/{self.event.pk}/','/staff/requests/','/staff/announcements/','/staff/announcements/new/']:
            with self.subTest(url=url): self.assertEqual(self.client.get(url).status_code,200)
    def test_public_auth_pages_render(self):
        self.client.logout()
        for url in ['/welcome/','/accounts/signup/','/accounts/login/','/accounts/password-reset/','/accounts/password-reset/done/','/accounts/reset/done/']:
            self.assertEqual(self.client.get(url).status_code,200)
    def test_no_school_private_data_for_another_school(self):
        self.client.force_login(self.stranger)
        self.assertNotContains(self.client.get('/events/'),'Test rehearsal')
        for suffix in ['', 'save/', 'request/']:
            response=self.client.post(f'/events/{self.event.pk}/{suffix}') if suffix else self.client.get(f'/events/{self.event.pk}/')
            self.assertEqual(response.status_code,404)
    def test_drafts_are_private(self):
        self.assertEqual(self.client.get(f'/events/{self.draft.pk}/').status_code,404)
        self.assertNotContains(self.client.get('/events/'),'Unpublished draft')
    def test_student_cannot_use_staff_endpoints(self):
        for url in ['/staff/','/staff/events/new/','/staff/requests/','/staff/announcements/']:
            self.assertEqual(self.client.get(url).status_code,403)
    def test_unverified_staff_cannot_use_staff_endpoints(self):
        self.staff_member.verified=False;self.staff_member.save()
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get('/staff/').status_code,403)
    def test_request_approval_wallet_notifications_history(self):
        self.assertEqual(self.client.post(f'/events/{self.event.pk}/request/').status_code,302)
        ticket=TicketRequest.objects.get(student=self.student)
        self.assertEqual(ticket.status,'requested')
        self.assertTrue(Notification.objects.filter(user=self.staff).exists())
        self.assertContains(self.client.get('/tickets/'),'not confirmed admission')
        decide(self.staff,self.staff_member,ticket.pk,'under_review')
        decide(self.staff,self.staff_member,ticket.pk,'approved','See you there')
        ticket.refresh_from_db()
        self.assertEqual(ticket.status,'approved');self.assertEqual(ticket.reviewed_by,self.staff)
        self.assertEqual(ticket.history.count(),3)
        self.assertEqual(self.event.remaining,0)
        self.assertContains(self.client.get('/tickets/'),"You're on the list",html=False)
        self.assertTrue(Notification.objects.filter(user=self.student,title='Ticket Approved').exists())
    def test_duplicate_active_request_rejected(self):
        request_ticket(self.student,self.member,self.event.pk)
        with self.assertRaises(ValueError): request_ticket(self.student,self.member,self.event.pk)
        self.assertEqual(TicketRequest.objects.count(),1)
    def test_database_blocks_duplicate_request(self):
        TicketRequest.objects.create(student=self.student,event=self.event)
        with self.assertRaises(IntegrityError):
            with transaction.atomic(): TicketRequest.objects.create(student=self.student,event=self.event)
    def test_capacity_prevents_second_approval(self):
        a=request_ticket(self.student,self.member,self.event.pk)
        b=request_ticket(self.student2,self.member2,self.event.pk)
        decide(self.staff,self.staff_member,a.pk,'approved')
        with self.assertRaises(ValueError): decide(self.staff,self.staff_member,b.pk,'approved')
        self.assertEqual(TicketRequest.objects.filter(status='approved').count(),1)
    def test_cancellation_releases_capacity_and_allows_new_request(self):
        a=request_ticket(self.student,self.member,self.event.pk)
        decide(self.staff,self.staff_member,a.pk,'approved')
        cancel(self.student,self.member,a.pk)
        self.assertEqual(self.event.remaining,1)
        request_ticket(self.student,self.member,self.event.pk)
        self.assertEqual(TicketRequest.objects.count(),2)
    def test_decline_is_not_approval(self):
        a=request_ticket(self.student,self.member,self.event.pk)
        decide(self.staff,self.staff_member,a.pk,'declined','Not eligible')
        self.assertContains(self.client.get('/tickets/'),'Declined')
        self.assertEqual(self.event.remaining,1)
    def test_cannot_decide_already_decided_request(self):
        a=request_ticket(self.student,self.member,self.event.pk)
        decide(self.staff,self.staff_member,a.pk,'declined')
        with self.assertRaises(ValueError): decide(self.staff,self.staff_member,a.pk,'approved')
    def test_student_cannot_decide_or_cancel_others(self):
        a=request_ticket(self.student2,self.member2,self.event.pk)
        self.assertEqual(self.client.post(f'/staff/requests/{a.pk}/decision/',{'status':'approved'}).status_code,403)
        self.assertEqual(self.client.post(f'/tickets/{a.pk}/cancel/').status_code,404)
    def test_unknown_price_exact_text(self): self.assertContains(self.client.get(f'/events/{self.event.pk}/'),'Price on request')
    def test_no_invented_capacity(self):
        self.event.capacity=None;self.event.save()
        self.assertNotContains(self.client.get(f'/events/{self.event.pk}/'),'spots available')
    def test_search_and_category(self):
        self.assertContains(self.client.get('/events/?q=Hall'),'Test rehearsal')
        self.assertNotContains(self.client.get('/events/?category=Sports'),'Test rehearsal')
        self.assertContains(self.client.get('/events/?q=no-match'),'No moments match just yet')
    def test_saves_and_collection_ownership(self):
        self.client.post(f'/events/{self.event.pk}/save/')
        self.assertEqual(SavedEvent.objects.filter(user=self.student).count(),1)
        self.client.post('/collections/new/',{'name':'Music nights','cover_style':'midnight'})
        c=Collection.objects.get(user=self.student)
        self.client.post(f'/collections/{c.pk}/action/',{'event':self.event.pk,'action':'add'})
        self.assertTrue(c.events.filter(pk=self.event.pk).exists())
        self.assertContains(self.client.get(f'/saved/?collection={c.pk}'),'Test rehearsal')
        self.client.force_login(self.student2)
        self.assertEqual(self.client.post(f'/collections/{c.pk}/action/',{'action':'delete'}).status_code,404)
        self.assertEqual(self.client.get(f'/collections/{c.pk}/').status_code,404)
        self.client.force_login(self.student)
        self.client.post(f'/events/{self.event.pk}/save/')
        self.assertFalse(c.events.exists())
    def test_invite_code_validation_and_no_self_promotion(self):
        user=User.objects.create_user('new@example.com',password='TestPassword!482')
        self.client.force_login(user)
        self.client.post('/join/',{'school':self.school.pk,'code':'incorrect','role':'staff'})
        self.assertFalse(Membership.objects.filter(user=user).exists())
        self.client.post('/join/',{'school':self.school.pk,'code':'private-test-invite','role':'staff'})
        self.assertEqual(Membership.objects.get(user=user).role,'student')
        self.assertNotContains(self.client.get('/profile/'),'private-test-invite')
    def test_staff_cannot_modify_other_school_event(self):
        self.client.force_login(self.staff)
        e=Event.objects.create(school=self.other,created_by=self.stranger,title='Other',category='Arts',description='Other',venue='Other',start_at=timezone.now()+timedelta(days=2))
        self.assertEqual(self.client.get(f'/staff/events/{e.pk}/').status_code,404)
    def test_scheduled_announcement_publishes_once(self):
        a=Announcement.objects.create(school=self.school,author=self.staff,title='Scheduled news',body='School update',status='scheduled',scheduled_for=timezone.now()-timedelta(minutes=1))
        publish_due(self.school);publish_due(self.school)
        a.refresh_from_db();self.assertEqual(a.status,'published')
        self.assertEqual(Notification.objects.filter(kind='announcement',title=a.title).count(),3)
        self.assertContains(self.client.get('/announcements/'),'Scheduled news')
    def test_future_and_draft_announcements_hidden(self):
        Announcement.objects.create(school=self.school,author=self.staff,title='Hidden future',body='No',status='scheduled',scheduled_for=timezone.now()+timedelta(days=1))
        self.assertNotContains(self.client.get('/announcements/'),'Hidden future')
    def test_published_pinned_announcement_and_edit(self):
        self.client.force_login(self.staff)
        self.client.post('/staff/announcements/new/',{'title':'Important news','body':'Read this','status':'published','is_pinned':'on'})
        a=Announcement.objects.get(title='Important news')
        self.assertTrue(a.is_pinned)
        self.assertEqual(Notification.objects.filter(title=a.title).count(),3)
        self.assertEqual(self.client.get(f'/staff/announcements/{a.pk}/').status_code,200)
        self.client.force_login(self.student)
        self.assertContains(self.client.get('/announcements/'),'PINNED')
    def test_notifications_private(self):
        item=Notification.objects.create(user=self.student2,school=self.school,title='Private note',message='Private',kind='ticket')
        self.assertNotContains(self.client.get('/notifications/'),'Private note')
        self.assertEqual(self.client.post(f'/notifications/{item.pk}/read/').status_code,404)
    def test_mutations_require_post_and_csrf(self):
        self.assertEqual(self.client.get(f'/events/{self.event.pk}/request/').status_code,405)
        client=Client(enforce_csrf_checks=True);client.force_login(self.student)
        self.assertEqual(client.post(f'/events/{self.event.pk}/request/').status_code,403)
    def test_xss_is_escaped(self):
        self.event.title='<script>alert(1)</script>';self.event.save()
        response=self.client.get(f'/events/{self.event.pk}/')
        self.assertNotContains(response,'<script>alert(1)</script>')
        self.assertContains(response,'&lt;script&gt;')
    def test_recovery_response_does_not_disclose_account(self):
        self.client.logout()
        a=self.client.post('/accounts/password-reset/',{'email':self.student.email})
        b=self.client.post('/accounts/password-reset/',{'email':'missing@example.com'})
        self.assertEqual(a.url,b.url)
    def test_auth_rate_limit(self):
        self.client.logout()
        for _ in range(30): self.client.post('/accounts/login/',{'username':'missing@example.com','password':'wrong'})
        self.assertEqual(self.client.post('/accounts/login/',{}).status_code,429)
    def test_signup_does_not_grant_membership(self):
        self.client.logout()
        self.client.post('/accounts/signup/',{'name':'New student','email':'signup@example.com','password1':'StrongTestPass!82','password2':'StrongTestPass!82','role':'staff'})
        user=User.objects.get(username='signup@example.com')
        self.assertFalse(user.is_staff);self.assertFalse(Membership.objects.filter(user=user).exists())
    def test_event_form_rejects_capacity_below_approved(self):
        a=request_ticket(self.student,self.member,self.event.pk);decide(self.staff,self.staff_member,a.pk,'approved')
        form=EventForm({'title':'Changed','category':'Music','venue':'Hall','description':'Text','start_at':(timezone.now()+timedelta(days=7)).strftime('%Y-%m-%dT%H:%M'),'capacity':'0','status':'published'},instance=self.event)
        self.assertFalse(form.is_valid());self.assertIn('capacity',form.errors)
    def test_invalid_announcement_schedule(self):
        form=AnnouncementForm({'title':'Note','body':'Text','status':'scheduled','scheduled_for':(timezone.now()-timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')})
        self.assertFalse(form.is_valid())

class SimultaneousApprovalTests(TransactionTestCase):
    def test_two_connections_cannot_overbook(self):
        # A file-backed test database is required to test actual SQLite writer locks.
        from django.db import connection
        if connection.vendor == 'sqlite':
            self.assertEqual(connection.settings_dict['OPTIONS']['transaction_mode'],'IMMEDIATE')
        else:
            self.assertTrue(connection.features.has_select_for_update)
        school=School.objects.create(name='Concurrency school',invite_code_hash=make_password('a-strong-test-invite'))
        staff=User.objects.create_user('reviewer');member=Membership.objects.create(user=staff,school=school,role='staff',verified=True)
        event=Event.objects.create(school=school,created_by=staff,title='One seat',category='Music',description='Test',venue='Hall',start_at=timezone.now()+timedelta(days=1),capacity=1,status='published')
        tickets=[]
        for i in range(2):
            user=User.objects.create_user(f'concurrent-{i}')
            Membership.objects.create(user=user,school=school)
            tickets.append(TicketRequest.objects.create(event=event,student=user))
        barrier=Barrier(2)
        def approve(pk):
            close_old_connections()
            try:
                local_staff=User.objects.get(pk=staff.pk);local_member=Membership.objects.get(pk=member.pk)
                barrier.wait(timeout=10)
                try: decide(local_staff,local_member,pk,'approved');return 'approved'
                except ValueError: return 'full'
            finally: close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(approve,[t.pk for t in tickets]))
        self.assertCountEqual(results,['approved','full'])
        self.assertEqual(TicketRequest.objects.filter(event=event,status='approved').count(),1)

class UploadSecurityTests(TransactionTestCase):
    def setUp(self):
        import tempfile
        self.storage=tempfile.TemporaryDirectory()
        self.override=override_settings(MEDIA_ROOT=self.storage.name)
        self.override.enable()
        self.addCleanup(self.override.disable);self.addCleanup(self.storage.cleanup)
        self.school=School.objects.create(name='Uploads',invite_code_hash=make_password('test-school-only'))
        self.staff=User.objects.create_user('upload-staff')
        Membership.objects.create(user=self.staff,school=self.school,role='staff',verified=True)
        self.client.force_login(self.staff)
    def image(self):
        from PIL import Image
        from io import BytesIO
        from django.core.files.uploadedfile import SimpleUploadedFile
        stream=BytesIO();Image.new('RGB',(32,32),'white').save(stream,format='PNG')
        return SimpleUploadedFile('safe.png',stream.getvalue(),content_type='image/png')
    def test_staff_image_upload_private_delivery_and_cross_school_denial(self):
        self.client.post('/staff/announcements/new/',{'title':'Image note','body':'A real test upload','status':'published','image':self.image()})
        item=Announcement.objects.get(title='Image note')
        response=self.client.get(f'/media/announcement/{item.pk}/')
        self.assertEqual(response.status_code,200);self.assertEqual(response['Cache-Control'],'private, no-store');response.close()
        other=School.objects.create(name='Other',invite_code_hash='unused')
        stranger=User.objects.create_user('other-student');Membership.objects.create(user=stranger,school=other)
        self.client.force_login(stranger)
        self.assertEqual(self.client.get(f'/media/announcement/{item.pk}/').status_code,404)
        self.client.logout()
        self.assertEqual(self.client.get(f'/media/announcement/{item.pk}/').status_code,302)
    def test_html_upload_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        response=self.client.post('/staff/announcements/new/',{'title':'Bad file','body':'No','status':'draft','image':SimpleUploadedFile('attack.png',b'<script>alert(1)</script>',content_type='image/png')})
        self.assertEqual(response.status_code,200)
        self.assertFalse(Announcement.objects.filter(title='Bad file').exists())

@override_settings(STORAGES={'default': {'BACKEND': 'community.storage.DatabasePrivateStorage'}, 'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class ServerlessUploadTests(UploadSecurityTests):
    def test_upload_survives_storage_instance_restart_without_public_url(self):
        from .storage import DatabasePrivateStorage
        storage=DatabasePrivateStorage()
        name=storage.save('events/example.png',self.image())
        restored=DatabasePrivateStorage()
        self.assertTrue(restored.exists(name))
        self.assertGreater(restored.size(name),0)
        with restored.open(name) as content: self.assertTrue(content.read().startswith(b'\x89PNG'))
        with self.assertRaises(ValueError): restored.url(name)
        restored.delete(name)
        self.assertFalse(storage.exists(name))
