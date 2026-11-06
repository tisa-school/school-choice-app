"""Public browsing, family permissions, recurring sessions, AI boundaries, and shared capacity."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.test import TestCase,TransactionTestCase,override_settings,Client
from django.db import close_old_connections,transaction,IntegrityError
from django.utils import timezone
from .models import *
from .services import express_interest,parent_decision,confirm_participation,decide
from .finder import recommendations,validate_filters,interpret,FinderUnavailable

class FeatureTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school=School.objects.create(name='Test community',invite_code_hash=make_password('private-test-code'))
        cls.staff=User.objects.create_user('staff@example.test',password='FamilyTesting!729',first_name='Test Staff')
        cls.staff_member=Membership.objects.create(user=cls.staff,school=cls.school,role='staff',verified=True)
        cls.parent=User.objects.create_user('parent@example.test',password='FamilyTesting!729')
        cls.account=ParentAccount.objects.create(user=cls.parent)
        cls.child=ChildProfile.objects.create(parent=cls.account,nickname='Test Child',age_band='9-11',interests='Art',languages='en')
        cls.other=User.objects.create_user('other@example.test',password='FamilyTesting!729')
        cls.other_account=ParentAccount.objects.create(user=cls.other)
        cls.other_child=ChildProfile.objects.create(parent=cls.other_account,nickname='Other private child',age_band='9-11')
        cls.student=User.objects.create_user('student@example.test',password='FamilyTesting!729')
        cls.member=Membership.objects.create(user=cls.student,school=cls.school,role='student',verified=True)
        common=dict(school=cls.school,created_by=cls.staff,category='Arts',description='Test listing',venue='Test venue',start_at=timezone.now()+timedelta(days=3),min_age=8,max_age=14,languages='en,pt',area='Lisbon',status='published')
        cls.event=Event.objects.create(**common,title='Public test event',visibility='public',published_by=cls.staff,capacity=1,price_amount=0)
        cls.private=Event.objects.create(**common,title='Private school test event')
        cls.activity=Event.objects.create(**common,title='Public test club',listing_type='activity',visibility='public',published_by=cls.staff)
        cls.session=ActivitySession.objects.create(activity=cls.activity,start_at=timezone.now()+timedelta(days=4),end_at=timezone.now()+timedelta(days=4,hours=2),capacity=1)
    def setUp(self): self.client.logout()
    def parent_login(self): self.client.force_login(self.parent)
    def pending(self,child=None,session=None,event=None):
        return Participation.objects.create(child=child or self.child,event=event or self.event,session=session,status='organizer_pending',parent_reviewed_at=timezone.now())
    def test_guest_opens_home_events_and_activities_without_login(self):
        for route in ['/','/events/','/activities/','/finder/',f'/events/{self.event.pk}/']:
            with self.subTest(route=route): self.assertEqual(self.client.get(route).status_code,200)
        self.assertContains(self.client.get('/'),'Discover')
    def test_private_listings_hidden_in_html_direct_urls_and_ai(self):
        self.assertNotContains(self.client.get('/'),'Private school test event')
        self.assertEqual(self.client.get(f'/events/{self.private.pk}/').status_code,404)
        self.assertFalse(any(r['event'].pk==self.private.pk for r in recommendations(self.parent,{})))
    def test_legacy_published_school_events_not_made_public(self):
        self.assertEqual(self.private.visibility,'school')
        self.assertEqual(self.client.get(f'/media/event/{self.private.pk}/').status_code,404)
    def test_publication_requires_recorded_staff_review(self):
        self.event.published_by=None;self.event.save()
        self.assertEqual(self.client.get(f'/events/{self.event.pk}/').status_code,404)
    def test_members_still_see_their_private_school_content(self):
        self.client.force_login(self.student)
        self.assertContains(self.client.get('/events/'),'Private school test event')
    def test_event_activity_views_are_distinct(self):
        self.assertContains(self.client.get('/activities/'),'Public test club')
        self.assertNotContains(self.client.get('/activities/'),'Public test event')
        self.assertNotContains(self.client.get('/events/'),'Public test club')
    def test_combined_filters_match_published_facts(self):
        self.assertContains(self.client.get('/events/?age=11&language=en&category=Arts&price=free&area=Lisbon'),'Public test event')
        for query in ['age=17','language=fr','price=paid','area=Porto','visibility=school','age=999999999999999999999999999']:
            with self.subTest(query=query): self.assertNotContains(self.client.get('/events/?'+query),'Public test event')
    def test_activity_day_filter_uses_actual_session(self):
        date=timezone.localtime(self.session.start_at).date()
        self.assertContains(self.client.get('/activities/?day='+str(date)),'Public test club')
        self.assertNotContains(self.client.get('/activities/?day=2020-01-01'),'Public test club')
    def test_unauthenticated_mutations_require_account(self):
        self.assertEqual(self.client.post(f'/events/{self.event.pk}/save/').status_code,302)
        self.assertEqual(self.client.post(f'/events/{self.event.pk}/interest/').status_code,302)
    def test_account_without_school_can_save_and_create_collections(self):
        self.parent_login();self.client.post(f'/events/{self.event.pk}/save/')
        self.assertTrue(SavedEvent.objects.filter(user=self.parent,event=self.event).exists())
        self.client.post('/collections/new/',{'name':'Family favorites','cover_style':'crystal'})
        self.assertTrue(Collection.objects.filter(user=self.parent,name='Family favorites').exists())
    def test_parent_cannot_access_other_family_profiles_or_requests(self):
        self.parent_login()
        self.assertNotContains(self.client.get('/family/'),'Other private child')
        self.assertEqual(self.client.get(f'/family/children/{self.other_child.pk}/').status_code,404)
        self.assertEqual(self.client.post(f'/events/{self.event.pk}/interest/',{'child':self.other_child.pk}).status_code,404)
        item=self.pending(child=self.other_child)
        self.assertEqual(self.client.post(f'/family/requests/{item.pk}/',{'action':'cancel'}).status_code,404)
    def test_student_cannot_self_grant_parent_role(self):
        self.client.force_login(self.student)
        self.assertEqual(self.client.post('/family/setup/',{'guardian_consent':'on'}).status_code,403)
        self.assertFalse(ParentAccount.objects.filter(user=self.student).exists())
    def test_new_adult_requires_explicit_guardian_declaration(self):
        adult=User.objects.create_user('newadult')
        self.client.force_login(adult)
        self.client.post('/family/setup/',{})
        self.assertFalse(ParentAccount.objects.filter(user=adult).exists())
        self.client.post('/family/setup/',{'guardian_consent':'on'})
        self.assertTrue(ParentAccount.objects.filter(user=adult).exists())
    def test_interest_parent_review_and_organizer_confirmation_are_distinct(self):
        item=express_interest(self.parent,self.event.pk,self.child.pk)
        self.assertEqual(item.status,'interested');self.assertEqual(self.event.remaining,1)
        parent_decision(self.parent,item.pk,'send')
        with self.assertRaises(ValueError): parent_decision(self.parent,item.pk,'approve','wrong')
        item=parent_decision(self.parent,item.pk,'approve','FamilyTesting!729')
        self.assertEqual(item.status,'organizer_pending');self.assertEqual(self.event.remaining,1)
        item=confirm_participation(self.staff,self.staff_member,item.pk,'confirmed')
        self.assertEqual(item.status,'confirmed');self.assertEqual(self.event.remaining,0)
        self.assertEqual(item.history.count(),4)
        self.assertTrue(Notification.objects.filter(user=self.parent,kind='family').exists())
    def test_organizer_cannot_confirm_before_parent_approval(self):
        item=express_interest(self.parent,self.event.pk,self.child.pk)
        with self.assertRaises(ValueError): confirm_participation(self.staff,self.staff_member,item.pk,'confirmed')
    def test_family_capacity_shared_with_legacy_tickets(self):
        item=self.pending();confirm_participation(self.staff,self.staff_member,item.pk,'confirmed')
        ticket=TicketRequest.objects.create(event=self.event,student=self.student)
        with self.assertRaises(ValueError): decide(self.staff,self.staff_member,ticket.pk,'approved')
    def test_legacy_approval_blocks_family_overbooking(self):
        item=self.pending();ticket=TicketRequest.objects.create(event=self.event,student=self.student)
        decide(self.staff,self.staff_member,ticket.pk,'approved')
        with self.assertRaises(ValueError): confirm_participation(self.staff,self.staff_member,item.pk,'confirmed')
    def test_session_confirmation_does_not_reserve_other_sessions(self):
        item=self.pending(event=self.activity,session=self.session)
        second=ActivitySession.objects.create(activity=self.activity,start_at=self.session.start_at+timedelta(days=7),end_at=self.session.end_at+timedelta(days=7),capacity=1)
        confirm_participation(self.staff,self.staff_member,item.pk,'confirmed')
        self.assertEqual(self.session.remaining,0);self.assertEqual(second.remaining,1)
    def test_wrong_session_and_duplicate_interest_rejected(self):
        with self.assertRaises(ActivitySession.DoesNotExist): express_interest(self.parent,self.activity.pk,self.child.pk,999999)
        express_interest(self.parent,self.activity.pk,self.child.pk,self.session.pk)
        with self.assertRaises(ValueError): express_interest(self.parent,self.activity.pk,self.child.pk,self.session.pk)
    def test_age_band_must_fit_listing_bounds(self):
        self.event.min_age=12;self.event.save()
        with self.assertRaises(ValueError): express_interest(self.parent,self.event.pk,self.child.pk)
    def test_cancellation_releases_confirmed_capacity(self):
        item=self.pending();confirm_participation(self.staff,self.staff_member,item.pk,'confirmed')
        parent_decision(self.parent,item.pk,'cancel')
        self.assertEqual(self.event.remaining,1)
    def test_family_plan_and_calendar_are_private_persistent_and_not_booking(self):
        self.parent_login();self.client.post(f'/events/{self.event.pk}/plan/')
        self.assertEqual(FamilyPlan.objects.filter(parent=self.account).count(),1)
        self.assertContains(self.client.get('/family/'),'Public test event')
        response=self.client.get('/family/calendar.ics')
        self.assertContains(response,'BEGIN:VCALENDAR');self.assertContains(response,'not a booking')
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get('/family/calendar.ics'),'Public test event')
    def test_staff_can_publish_public_listing_with_review_audit(self):
        self.client.force_login(self.staff)
        payload={'title':'Staff public activity','category':'Science','description':'Test','start_at':(timezone.now()+timedelta(days=7)).strftime('%Y-%m-%dT%H:%M'),'venue':'Test hall','listing_type':'activity','visibility':'public','status':'published','languages':'EN, pt','min_age':8,'max_age':14}
        self.client.post('/staff/events/new/',payload)
        item=Event.objects.get(title='Staff public activity')
        self.assertEqual(item.published_by,self.staff);self.assertEqual(item.languages,'en,pt')
    def test_session_form_validation_and_cancellation(self):
        item=self.pending(event=self.activity,session=self.session);confirm_participation(self.staff,self.staff_member,item.pk,'confirmed')
        self.client.force_login(self.staff)
        payload={'start_at':self.session.start_at.strftime('%Y-%m-%dT%H:%M'),'end_at':self.session.end_at.strftime('%Y-%m-%dT%H:%M'),'capacity':1,'is_cancelled':'on'}
        self.client.post(f'/staff/activities/{self.activity.pk}/sessions/{self.session.pk}/',payload)
        item.refresh_from_db();self.assertEqual(item.status,'cancelled')
    def test_external_organizer_cannot_publish_or_verify_identity(self):
        user=User.objects.create_user('external')
        Membership.objects.create(user=user,school=self.school,role='organizer',verified=True)
        self.client.force_login(user)
        payload={'title':'External submission','category':'Arts','description':'Test','start_at':(timezone.now()+timedelta(days=7)).strftime('%Y-%m-%dT%H:%M'),'venue':'Test hall','status':'published','identity_verified':'on','visibility':'public'}
        self.client.post('/organizer/',payload)
        item=Event.objects.get(title='External submission')
        self.assertEqual(item.status,'submitted');self.assertFalse(item.identity_verified);self.assertIsNone(item.published_by)
        self.client.logout();self.assertEqual(self.client.get(f'/events/{item.pk}/').status_code,404)
    @override_settings(AI_API_KEY='')
    def test_ai_unavailable_does_not_break_discovery(self):
        with self.assertRaises(FinderUnavailable): interpret('art')
        response=self.client.get('/finder/')
        self.assertContains(response,'name="search"');self.assertContains(response,'Find matching activities')
        self.assertEqual(self.client.get('/activities/').status_code,200)
    def test_ai_never_selects_private_full_or_age_ineligible_listings(self):
        results=recommendations(self.parent,{'age':'11','language':'en','category':'Arts'})
        self.assertIn(self.event.pk,[r['event'].pk for r in results])
        self.assertNotIn(self.private.pk,[r['event'].pk for r in results])
        item=self.pending();confirm_participation(self.staff,self.staff_member,item.pk,'confirmed')
        self.assertNotIn(self.event.pk,[r['event'].pk for r in recommendations(self.parent,{'age':'11'})])
        self.assertEqual(recommendations(self.parent,{'age':'17'}),[])
    @patch('community.finder.interpret',return_value={'age':'11','language':'en','category':'Arts'})
    def test_ai_results_link_to_authorized_source_listings(self,mock):
        response=self.client.post('/finder/',{'preferences':'Art, age 11, English','consent':'on'})
        self.assertContains(response,f'/events/{self.event.pk}/')
        self.assertNotContains(response,'Private school test event')
        mock.assert_called_once_with('Art, age 11, English')
    @patch('community.finder.interpret')
    def test_ai_requires_explicit_preferences_only_consent(self,mock):
        self.client.post('/finder/',{'preferences':'Art'})
        mock.assert_not_called()
    def test_ai_filter_validation_rejects_arbitrary_fields_and_invalid_values(self):
        with self.assertRaises(ValueError): validate_filters({'age':999})
        data=validate_filters({'category':'Arts','age':11,'language':'en','area':'','day':'','price':'','period':'','event_id':self.private.pk})
        self.assertNotIn('event_id',data)
    def test_family_pages_render_and_do_not_collect_birth_dates(self):
        self.parent_login()
        for route in ['/family/','/family/children/new/','/saved/','/notifications/','/profile/']:
            with self.subTest(route=route): self.assertEqual(self.client.get(route).status_code,200)
        self.assertNotContains(self.client.get('/family/children/new/'),'date_of_birth')
    def test_malformed_family_ids_are_rejected_without_server_error(self):
        self.parent_login()
        self.assertEqual(self.client.post(f'/events/{self.event.pk}/interest/',{'child':'invalid'}).status_code,404)
    def test_saves_require_csrf(self):
        client=Client(enforce_csrf_checks=True);client.force_login(self.parent)
        self.assertEqual(client.post(f'/events/{self.event.pk}/save/').status_code,403)

class FamilyCapacityRaceTests(TransactionTestCase):
    def test_legacy_and_family_approvals_compete_for_one_place(self):
        school=School.objects.create(name='Race test school',invite_code_hash=make_password('only-for-tests'))
        staff=User.objects.create_user('race-staff');member=Membership.objects.create(user=staff,school=school,role='staff',verified=True)
        student=User.objects.create_user('race-student');Membership.objects.create(user=student,school=school,verified=True)
        parent=User.objects.create_user('race-parent');account=ParentAccount.objects.create(user=parent);child=ChildProfile.objects.create(parent=account,nickname='Private test child',age_band='9-11')
        event=Event.objects.create(school=school,created_by=staff,published_by=staff,title='Single place race',min_age=8,max_age=14,category='Arts',description='Test',venue='Test',start_at=timezone.now()+timedelta(days=2),capacity=1,status='published',visibility='public')
        ticket=TicketRequest.objects.create(event=event,student=student)
        item=Participation.objects.create(event=event,child=child,status='organizer_pending')
        barrier=Barrier(2)
        def approve(which):
            close_old_connections()
            try:
                user=User.objects.get(pk=staff.pk);membership=Membership.objects.get(pk=member.pk);barrier.wait(timeout=10)
                try:
                    if which=='family': confirm_participation(user,membership,item.pk,'confirmed')
                    else: decide(user,membership,ticket.pk,'approved')
                    return 'confirmed'
                except ValueError: return 'full'
            finally: close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool: outcomes=list(pool.map(approve,['family','legacy']))
        self.assertCountEqual(outcomes,['confirmed','full'])
        event.refresh_from_db();self.assertEqual(event.remaining,0)

class DeploymentPrivacyTests(TestCase):
    @classmethod
    def setUpTestData(cls): FeatureTests.setUpTestData.__func__(cls)
    def parent_login(self): self.client.force_login(self.parent)
    def pending(self): return Participation.objects.create(child=self.child,event=self.event,status='organizer_pending')
    def test_authenticated_family_rate_limits_do_not_throttle_other_families(self):
        self.parent_login()
        for _ in range(30): self.client.post('/collections/new/',{})
        self.assertEqual(self.client.post('/collections/new/',{}).status_code,429)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post('/collections/new/',{}).status_code,200)
    def test_confirmation_rechecks_changed_age_band(self):
        item=self.pending()
        self.child.age_band='15-17';self.child.save()
        with self.assertRaises(ValueError): confirm_participation(self.staff,self.staff_member,item.pk,'confirmed')
    def test_revoked_membership_does_not_expose_private_updated_listing(self):
        Membership.objects.create(user=self.parent,school=self.school,role='parent',verified=True)
        FamilyPlan.objects.create(parent=self.account,event=self.private)
        Participation.objects.create(child=self.child,event=self.private)
        Membership.objects.filter(user=self.parent).delete()
        self.private.title='Changed private title after revocation';self.private.save()
        self.parent_login()
        self.assertNotContains(self.client.get('/family/'),'Changed private title after revocation')
        self.assertNotContains(self.client.get('/family/calendar.ics'),'Changed private title after revocation')
