"""Behavioral regressions for shared seats, content ownership, private media and language preference."""
import json,tempfile
from io import BytesIO
from django.test import TestCase,Client,override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image
from . import test_features as fixtures
from .models import *
from .attendance import book_family,decide_booking
from .services import decide,confirm_participation
from .organizers import cancel_listing
from .community_forms import TeamPhotoForm,ExperienceForm,clean_photo
from .localization import ACTIVE_LOCALES,catalog

def photo():
    out=BytesIO();Image.new('RGB',(32,32),'purple').save(out,'JPEG')
    return SimpleUploadedFile('photo.jpg',out.getvalue(),content_type='image/jpeg')

@override_settings(MEDIA_ROOT=tempfile.gettempdir()+'/tkzone-expansion-tests')
class ExpansionTests(TestCase):
    @classmethod
    def setUpTestData(cls):fixtures.FeatureTests.setUpTestData.__func__(cls)
    def setUp(self):self.event.capacity=6;self.event.child_capacity=2;self.event.save()
    def booking(self,adults=2,children=2):return book_family(self.parent,self.event.pk,adults,children)
    def test_total_and_children_share_capacity_and_cancel_releases(self):
        item=self.booking();self.assertEqual(self.event.attendance['total'],0)
        decide_booking(self.staff,item.pk,'confirm');self.assertEqual(self.event.attendance['total'],4);self.assertEqual(self.event.remaining,2);self.assertEqual(self.event.remaining_children,0)
        with self.assertRaises(ValueError):book_family(self.other,self.event.pk,0,1)
        adult=book_family(self.other,self.event.pk,2,0);decide_booking(self.staff,adult.pk,'confirm');self.assertEqual(self.event.remaining,0)
        decide_booking(self.parent,item.pk,'cancel');self.assertEqual(self.event.remaining,4)
    def test_pending_requests_recheck_both_limits_at_confirmation(self):
        first=self.booking();second=book_family(self.other,self.event.pk,1,1)
        decide_booking(self.staff,first.pk,'confirm')
        with self.assertRaises(ValueError):decide_booking(self.staff,second.pk,'confirm')
        self.assertEqual(FamilyBooking.objects.get(pk=second.pk).status,'pending')
    def test_legacy_school_ticket_counts_as_child_and_cannot_overbook(self):
        self.event.capacity=3;self.event.child_capacity=1;self.event.save()
        item=self.booking(2,1);decide_booking(self.staff,item.pk,'confirm')
        ticket=TicketRequest.objects.create(event=self.event,student=self.student)
        with self.assertRaises(ValueError):decide(self.staff,self.staff_member,ticket.pk,'approved')
    def test_unauthorized_confirmation_and_cancellation_rejected(self):
        item=self.booking()
        for user,action in [(self.parent,'confirm'),(self.other,'cancel')]:
            with self.assertRaises(PermissionError):decide_booking(user,item.pk,action)
    def test_duplicate_and_invalid_registrations_rejected(self):
        self.booking()
        with self.assertRaises(ValueError):self.booking()
        for counts in [(0,0),(-1,2),(1,1001)]:
            with self.assertRaises(ValueError):book_family(self.other,self.event.pk,*counts)
    def test_event_cancellation_cancels_group_bookings(self):
        item=self.booking();cancel_listing(self.staff,self.staff_member,self.event.pk,'The venue is closed for maintenance.')
        item.refresh_from_db();self.assertEqual(item.status,'cancelled');self.assertTrue(Notification.objects.filter(user=self.parent,link='/family/').exists())
    def test_capacity_form_cannot_shrink_below_confirmed_groups(self):
        from .forms import EventForm
        item=self.booking();decide_booking(self.staff,item.pk,'confirm')
        form=EventForm({'capacity':3,'child_capacity':1},instance=self.event);form.is_valid()
        self.assertIn('capacity',form.errors);self.assertIn('child_capacity',form.errors)
    def test_comment_owner_edit_delete_and_moderation(self):
        self.client.force_login(self.parent)
        url=f'/events/{self.event.pk}/experiences/new/'
        response=self.client.post(url,{'body':'A lovely supervised activity.'});self.assertEqual(response.status_code,302)
        item=EventExperience.objects.get();self.assertEqual(item.status,'pending')
        self.assertNotContains(Client().get(f'/events/{self.event.pk}/'),'A lovely supervised activity.')
        self.client.force_login(self.other);self.assertEqual(self.client.post(f'/experiences/{item.pk}/delete/').status_code,404)
        self.client.force_login(self.staff);self.client.post(f'/staff/content/{item.pk}/publish/')
        self.assertContains(Client().get(f'/events/{self.event.pk}/'),'A lovely supervised activity.')
        self.client.force_login(self.parent);self.client.post(f'/events/{self.event.pk}/experiences/{item.pk}/edit/',{'body':'Edited review for moderation.'})
        item.refresh_from_db();self.assertEqual(item.status,'pending')
    def test_multiple_photo_validation_and_private_media(self):
        form=ExperienceForm({'body':'Our visit','photo_description':'An activity table','permission':'on'},{'photos':[photo(),photo()]})
        self.assertTrue(form.is_valid(),form.errors);self.assertEqual(len(form.cleaned_data['photos']),2)
        item=EventExperience.objects.create(event=self.event,author=self.parent,body='Visit')
        image=ExperiencePhoto.objects.create(experience=item,image=clean_photo(photo()),description='Activity table')
        url=f'/protected-photos/experience/{image.pk}/'
        self.assertEqual(Client().get(url).status_code,404)
        self.client.force_login(self.parent);self.assertEqual(self.client.get(url).status_code,200)
        item.status='published';item.save();self.assertEqual(Client().get(url).status_code,200)
        image.hidden=True;image.save();self.assertEqual(Client().get(url).status_code,404)
    def test_photo_permission_required_and_non_image_rejected(self):
        form=ExperienceForm({'body':'Visit','photo_description':'Activity table'},{'photos':[photo()]});self.assertFalse(form.is_valid());self.assertIn('permission',form.errors)
        bad=SimpleUploadedFile('bad.jpg',b'<script>alert(1)</script>',content_type='image/jpeg')
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):clean_photo(bad)
    def test_team_photo_default_private_and_names_first_only(self):
        image=TeamPhoto.objects.create(school=self.school,uploaded_by=self.staff,name='Student Fullname',is_student=True,image=clean_photo(photo()),description='Student portrait')
        self.assertEqual(image.display_name,'Student');self.assertEqual(image.visibility,'private')
        url=f'/protected-photos/team/{image.pk}/';self.assertEqual(Client().get(url).status_code,404)
        self.client.force_login(self.staff);self.assertEqual(self.client.get(url).status_code,200)
        image.visibility='public';image.sharing_permission=True;image.save();self.assertEqual(Client().get(url).status_code,404)
        image.guardian_consent=True;image.save();self.assertEqual(Client().get(url).status_code,200)
        self.assertNotContains(Client().get('/team/photos/'),'Student Fullname')
    def test_student_and_group_photos_require_consent_before_sharing(self):
        form=TeamPhotoForm({'school':self.school.pk,'name':'Student Name','description':'Portrait','is_student':'on','visibility':'public','sharing_permission':'on'}, {'image':photo()})
        self.assertFalse(form.is_valid());self.assertIn('guardian_consent',form.errors)
    def test_reports_require_visibility_and_are_deduplicated(self):
        item=EventExperience.objects.create(event=self.event,author=self.parent,body='Visit',status='published');self.client.force_login(self.other)
        for _ in range(2):self.client.post(f'/experiences/{item.pk}/report/',{'reason':'This should be reviewed.'})
        self.assertEqual(item.reports.count(),1);self.assertEqual(self.client.get('/staff/content/').status_code,404)
    def test_ten_requested_languages_rtl_and_account_preference(self):
        expected={'en','zh-CN','hi','es','ar','fr','bn','pt-PT','ru','ur'};self.assertTrue(expected<=set(ACTIVE_LOCALES))
        for code in expected:
            response=Client().get('/about/',{'lang':code});self.assertEqual(response.status_code,200);self.assertEqual(response['Content-Language'],code)
            self.assertContains(response,'dir="rtl"' if code in ['ar','ur'] else 'dir="ltr"')
            self.assertEqual(set(catalog(code)),set(catalog('en')))
            self.assertTrue(all(catalog(code).values()))
        self.client.force_login(self.parent);self.client.get('/about/?lang=ar');other=Client();other.force_login(self.parent)
        self.assertEqual(other.get('/about/')['Content-Language'],'ar')
        self.assertEqual(InterfacePreference.objects.get(user=self.parent).language,'ar')
    def test_interface_translation_preserves_authored_names_and_html(self):
        self.event.title='Home';self.event.save()
        response=self.client.get(f'/events/{self.event.pk}/?lang=es');self.assertContains(response,'data-user-content');self.assertContains(response,'Home')
        self.assertNotContains(response,'<script>alert(1)</script>')

from django.test import TransactionTestCase
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.db import close_old_connections
from django.contrib.auth.hashers import make_password
from datetime import timedelta

class GroupCapacityRaceTests(TransactionTestCase):
    def test_group_and_school_ticket_compete_for_child_limit(self):
        school=School.objects.create(name='Race school',invite_code_hash=make_password('test-only'))
        staff=User.objects.create_user('group-race-staff');member=Membership.objects.create(user=staff,school=school,role='staff',verified=True)
        parent=User.objects.create_user('group-race-parent');account=ParentAccount.objects.create(user=parent)
        student=User.objects.create_user('group-race-student')
        event=Event.objects.create(school=school,created_by=staff,published_by=staff,title='Child limit race',category='Arts',description='Test',venue='Test',start_at=timezone.now()+timedelta(days=2),capacity=4,child_capacity=1,status='published',visibility='public')
        booking=FamilyBooking.objects.create(parent=account,event=event,adults=2,children=1)
        ticket=TicketRequest.objects.create(event=event,student=student)
        barrier=Barrier(2)
        def approve(which):
            close_old_connections()
            try:
                user=User.objects.get(pk=staff.pk);membership=Membership.objects.get(pk=member.pk);barrier.wait(timeout=10)
                try:
                    if which=='group':decide_booking(user,booking.pk,'confirm')
                    else:decide(user,membership,ticket.pk,'approved')
                    return 'confirmed'
                except ValueError:return 'full'
            finally:close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:outcomes=list(pool.map(approve,['group','school']))
        self.assertCountEqual(outcomes,['confirmed','full']);self.assertEqual(event.attendance['children'],1);self.assertLessEqual(event.attendance['total'],4)

class AdditionalPrivacyTests(TestCase):
    @classmethod
    def setUpTestData(cls):fixtures.FeatureTests.setUpTestData.__func__(cls)
    # Keep only these additional cases in this class; base coverage runs once above.
    def test_moderator_can_review_photos_after_listing_unpublished(self):
        item=EventExperience.objects.create(event=self.event,author=self.parent,body='Pending')
        image=ExperiencePhoto.objects.create(experience=item,image=clean_photo(photo()),description='Review image')
        self.event.status='draft';self.event.save()
        self.client.force_login(self.staff);self.assertEqual(self.client.get(f'/protected-photos/experience/{image.pk}/').status_code,200)
        self.client.force_login(self.other);self.assertEqual(self.client.get(f'/protected-photos/experience/{image.pk}/').status_code,404)
    def test_student_cannot_submit_photos_or_bypass_moderation(self):
        self.client.force_login(self.student)
        self.assertEqual(self.client.post(f'/events/{self.event.pk}/experiences/new/',{'body':'Attempt'}).status_code,403)
        self.assertFalse(EventExperience.objects.exists())
    def test_markup_in_comments_is_escaped(self):
        EventExperience.objects.create(event=self.event,author=self.parent,body='<script>alert(1)</script>',status='published')
        response=self.client.get(f'/events/{self.event.pk}/')
        self.assertNotContains(response,'<script>alert(1)</script>');self.assertContains(response,'&lt;script&gt;')
    def test_school_and_brand_are_not_translated(self):
        en=catalog('en')
        for language in ACTIVE_LOCALES:
            for key,value in en.items():
                for name in ['Unicorn School','TK-Zone','TK-ZONE']:
                    if name in value:self.assertIn(name,catalog(language)[key],(language,key))
    def test_csrf_protects_booking_confirmation(self):
        item=FamilyBooking.objects.create(parent=self.account,event=self.event,adults=1,children=1)
        client=Client(enforce_csrf_checks=True);client.force_login(self.staff)
        self.assertEqual(client.post(f'/registrations/{item.pk}/confirm/').status_code,403)
        item.refresh_from_db();self.assertEqual(item.status,'pending')
