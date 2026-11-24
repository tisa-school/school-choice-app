"""Mobile API tests use an isolated test database and fictional fixtures only."""
from datetime import timedelta
from django.test import TestCase,override_settings,Client
from django.contrib.auth.models import User
from django.utils import timezone
from .models import School,Event,ParentAccount,ChildProfile,MobileSession,MobilePushDevice,MobileDeletionRequest,SavedEvent,Notification,Participation,Membership,SchoolProfile
from .mobile_api import digest

@override_settings(MOBILE_API_ENABLED=True)
class MobileTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.parent=User.objects.create_user('mobile-parent',password='StrongMobile!482')
        cls.other=User.objects.create_user('other-parent',password='StrongMobile!482')
        cls.owner=ParentAccount.objects.create(user=cls.parent)
        ParentAccount.objects.create(user=cls.other)
        cls.child=ChildProfile.objects.create(parent=cls.owner,nickname='Fictional child',age_band='9-11',languages='en',interests='Arts')
        cls.school=School.objects.create(name='Fictional school')
        cls.event=Event.objects.create(school=cls.school,created_by=cls.parent,title='Fictional art workshop',description='Test only',category='Arts',venue='Test venue',area='Lisbon',languages='en',min_age=7,max_age=12,visibility='public',published_by=cls.parent,status='published',start_at=timezone.now()+timedelta(days=5),end_at=timezone.now()+timedelta(days=5,hours=1),price_amount=0)
        cls.private=Event.objects.create(school=cls.school,created_by=cls.parent,title='Private event',category='Arts',venue='Private',start_at=timezone.now()+timedelta(days=3),status='published')
    def setUp(self):
        self.client=Client();self.raw=self.client.post('/mobile/v1/auth/login/',{'username':'mobile-parent','password':'StrongMobile!482','platform':'ios'},content_type='application/json').json()['token']
        self.auth={'HTTP_AUTHORIZATION':'Bearer '+self.raw}
    def post(self,path,body,auth=True):return self.client.post('/mobile/v1'+path,body,content_type='application/json',**(self.auth if auth else {}))
    def test_token_is_only_hashed_and_expires(self):
        self.assertTrue(MobileSession.objects.filter(token_hash=digest(self.raw)).exists())
        self.assertFalse(MobileSession.objects.filter(token_hash=self.raw).exists())
        MobileSession.objects.update(expires_at=timezone.now()-timedelta(seconds=1))
        self.assertEqual(self.client.get('/mobile/v1/me/',**self.auth).status_code,401)
    @override_settings(MOBILE_API_ENABLED=False)
    def test_disabled_by_default(self):self.assertEqual(self.client.get('/mobile/v1/events/').status_code,404)
    def test_cookie_does_not_grant_mobile_access(self):
        self.client.force_login(self.parent);self.assertEqual(self.client.get('/mobile/v1/me/').status_code,401)
    def test_cors(self):
        self.assertEqual(self.client.get('/mobile/v1/events/',HTTP_ORIGIN='https://evil.example').status_code,403)
        response=self.client.options('/mobile/v1/me/',HTTP_ORIGIN='capacitor://localhost')
        self.assertEqual(response.status_code,204);self.assertEqual(response['Access-Control-Allow-Origin'],'capacitor://localhost')
        self.assertNotIn('Access-Control-Allow-Credentials',response)
    def test_generic_login_error(self):
        for name in ['mobile-parent','does-not-exist']:
            response=self.post('/auth/login/',{'username':name,'password':'wrong'},False)
            self.assertEqual(response.status_code,401);self.assertIn('Unable to sign in',response.json()['error'])
    def test_public_discovery_and_combined_filters(self):
        response=self.client.get('/mobile/v1/events/?age=11&category=Arts&area=Lisbon&language=en&price=free')
        self.assertEqual(response.status_code,200);self.assertEqual([x['id'] for x in response.json()['items']],[self.event.pk])
        self.assertEqual(self.client.get('/mobile/v1/events/?age=16').json()['items'],[])
    def test_school_scope_and_drafts(self):
        self.assertEqual(self.client.get(f'/mobile/v1/events/{self.private.pk}/',**self.auth).status_code,404)
        self.event.status='draft';self.event.save();self.assertEqual(self.client.get(f'/mobile/v1/events/{self.event.pk}/').status_code,404)
    def test_saves_persist_and_are_private(self):
        self.assertEqual(self.post(f'/events/{self.event.pk}/save/',{'saved':True}).status_code,200)
        self.assertTrue(SavedEvent.objects.filter(user=self.parent,event=self.event).exists())
        self.post(f'/events/{self.event.pk}/save/',{'saved':True});self.assertEqual(SavedEvent.objects.count(),1)
        self.post(f'/events/{self.event.pk}/save/',{'saved':False});self.assertEqual(SavedEvent.objects.count(),0)
    def test_request_duplicate_and_parent_password_decision(self):
        body={'event_id':self.event.pk,'child_id':self.child.pk}
        response=self.post('/family/requests/',body);self.assertEqual(response.status_code,201,response.content)
        pk=response.json()['id'];self.assertEqual(self.post('/family/requests/',body).status_code,400)
        self.assertEqual(self.post(f'/family/requests/{pk}/decision/',{'action':'approve','password':'wrong'}).status_code,400)
        response=self.post(f'/family/requests/{pk}/decision/',{'action':'approve','password':'StrongMobile!482'})
        self.assertEqual(response.status_code,200,response.content);self.assertEqual(response.json()['status'],'organizer_pending')
    def test_cannot_request_another_parents_child(self):
        raw=self.post('/auth/login/',{'username':'other-parent','password':'StrongMobile!482'},False).json()['token'];self.auth={'HTTP_AUTHORIZATION':'Bearer '+raw}
        self.assertEqual(self.post('/family/requests/',{'event_id':self.event.pk,'child_id':self.child.pk}).status_code,404)
        self.assertEqual(self.client.get('/mobile/v1/family/',**self.auth).json()['children'],[])
    def test_calendar_plan_is_idempotent_not_booking(self):
        for _ in range(2):self.assertEqual(self.post('/family/calendar/',{'event_id':self.event.pk}).status_code,200)
        self.assertEqual(len(self.client.get('/mobile/v1/family/calendar/',**self.auth).json()['items']),1)
        self.assertEqual(Participation.objects.count(),0)
    def test_notification_ownership(self):
        notice=Notification.objects.create(user=self.other,school=self.school,kind='event',title='Private',message='Private')
        self.assertEqual(self.post(f'/notifications/{notice.pk}/read/',{}).status_code,404)
        self.assertEqual(self.client.get('/mobile/v1/notifications/',**self.auth).json()['items'],[])
    def test_push_requires_adult_consent_and_native_session(self):
        self.assertEqual(self.post('/push/device/',{'token':'t'*64,'consent':False}).status_code,400)
        self.assertEqual(self.post('/push/device/',{'token':'t'*64,'consent':True}).status_code,200)
        self.assertEqual(MobilePushDevice.objects.count(),1)
        ParentAccount.objects.filter(user=self.parent).delete()
        self.assertEqual(self.post('/push/device/',{'token':'t'*64,'consent':True}).status_code,403)
    def test_logout_revokes_session_and_push(self):
        self.post('/push/device/',{'token':'t'*64,'consent':True})
        self.assertEqual(self.post('/auth/logout/',{}).status_code,200)
        self.assertEqual(self.client.get('/mobile/v1/me/',**self.auth).status_code,401);self.assertEqual(MobilePushDevice.objects.count(),0)
    def test_deletion_request_not_claimed_completed(self):
        response=self.post('/privacy/deletion-request/',{'password':'StrongMobile!482'})
        self.assertEqual(response.status_code,202);self.assertTrue(MobileDeletionRequest.objects.filter(status='pending').exists())
        self.assertEqual(self.client.get('/mobile/v1/me/',**self.auth).status_code,401);self.assertTrue(User.objects.filter(pk=self.parent.pk).exists())
    def test_malformed_body_and_methods(self):
        self.assertEqual(self.post('/me/',[]).status_code,400)
        self.assertEqual(self.post('/me/',{'name':{}}).status_code,400)
        self.assertEqual(self.client.put('/mobile/v1/me/','{}',content_type='application/json',**self.auth).status_code,405)
    def test_unknown_price_is_exact(self):
        self.event.price_amount=None;self.event.save()
        self.assertEqual(self.client.get(f'/mobile/v1/events/{self.event.pk}/').json()['event']['price'],'Price on request')
    def test_native_school_links_are_public(self):
        school=SchoolProfile.objects.create(name='Fictional profile',slug='fictional',is_published=True)
        response=self.client.get('/mobile/v1/schools/')
        self.assertEqual(response.status_code,200,response.content);self.assertEqual(response.json()['items'][0]['name'],school.name)
