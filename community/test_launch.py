"""Regression checks for production user journeys and newly completed controls."""
import re,tempfile
from django.test import TestCase,Client,override_settings
from django.contrib.auth.models import User
from django.core import mail
from . import test_about_refresh
from .models import Feedback,TeamPhoto,Membership

@override_settings(MEDIA_ROOT=tempfile.gettempdir()+'/tkzone-launch-tests',EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',AI_API_KEY='')
class LaunchTests(TestCase):
    setUpTestData=classmethod(test_about_refresh.AboutRefreshTests.setUpTestData.__func__)
    portrait=test_about_refresh.AboutRefreshTests.portrait
    def test_photo_can_be_published_and_hidden_without_upload_or_code_deployment(self):
        photo=self.portrait(name='Sophia Gateneo',is_student=True)
        self.client.force_login(self.staff)
        url='/team/portraits/student-1/'
        self.assertEqual(self.client.post(url,{'action':'publish'},HTTP_X_REQUESTED_WITH='XMLHttpRequest').status_code,400)
        photo.refresh_from_db();self.assertEqual(photo.visibility,'private')
        response=self.client.post(url,{'action':'publish','publish_consent':'on'},HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code,200);self.assertEqual(response.json()['visibility'],'public')
        photo.refresh_from_db();self.assertTrue(photo.sharing_permission and photo.guardian_consent)
        self.assertEqual(Client().get(f'/protected-photos/team/{photo.pk}/').status_code,200)
        self.assertContains(Client().get('/about/'),f'/protected-photos/team/{photo.pk}/')
        response=self.client.post(url,{'action':'private'},HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code,200)
        self.assertEqual(Client().get(f'/protected-photos/team/{photo.pk}/').status_code,404)
    def test_photo_publishing_requires_real_scoped_staff_and_csrf(self):
        photo=self.portrait()
        self.client.force_login(self.parent)
        self.assertEqual(self.client.post('/team/portraits/lead/',{'action':'publish','publish_consent':'on'}).status_code,404)
        client=Client(enforce_csrf_checks=True);client.force_login(self.staff)
        self.assertEqual(client.post('/team/portraits/lead/',{'action':'publish','publish_consent':'on'}).status_code,403)
        self.client.force_login(self.staff);self.school.name='Other school';self.school.save()
        self.assertEqual(self.client.post('/team/portraits/lead/',{'action':'publish','publish_consent':'on'}).status_code,404)
        photo.refresh_from_db();self.assertEqual(photo.visibility,'private')
    def test_finder_works_without_ai_and_validates_filters(self):
        response=self.client.get('/finder/',{'search':'1','category':'Arts','age':'11','language':'en','price':'free'})
        self.assertContains(response,self.event.title);self.assertNotContains(response,self.private.title)
        self.assertContains(response,f'/events/{self.event.pk}/')
        self.assertNotContains(self.client.get('/finder/',{'search':'1','age':'99'}),self.event.title)
        response=self.client.get('/finder/',{'search':'1','category':'Sports'})
        self.assertContains(response,'No suitable matches this time.')
    def test_general_feedback_is_routed_to_school_review(self):
        self.client.post('/feedback/',{'kind':'feedback','message':'Please review this school feedback.','consent':'on'})
        item=Feedback.objects.get();self.assertEqual(item.school,self.school)
        self.client.force_login(self.staff)
        self.assertContains(self.client.get('/staff/feedback/'),item.message)
        old=Feedback.objects.create(kind='feedback',message='Previously unassigned feedback')
        self.assertContains(self.client.get('/staff/feedback/'),old.message)
        self.client.post(f'/staff/feedback/{item.pk}/',{'status':'resolved'})
        item.refresh_from_db();self.assertEqual(item.status,'resolved')
    def test_staff_can_configure_invite_code_with_reauthentication(self):
        self.client.force_login(self.staff)
        data={'code':'New-private-school-code!','password':'wrong'}
        self.assertEqual(self.client.post('/staff/school/',data).status_code,200)
        self.school.refresh_from_db();self.assertFalse(self.school.valid_invite(data['code']))
        data['password']='FamilyTesting!729'
        self.assertRedirects(self.client.post('/staff/school/',data),'/staff/school/')
        self.school.refresh_from_db();self.assertTrue(self.school.valid_invite(data['code']))
        user=User.objects.create_user('new-family@example.test',password='IsolatedSignup!729')
        self.client.force_login(user)
        self.assertEqual(self.client.get('/staff/school/').status_code,302)
        self.assertRedirects(self.client.post('/join/',{'school':self.school.pk,'code':data['code']}),'/')
        self.assertEqual(Membership.objects.get(user=user).role,'student')
        self.assertEqual(self.client.post('/staff/school/',data).status_code,403)
    def test_password_recovery_link_resets_password_and_authenticates(self):
        user=User.objects.create_user('recover@example.test',email='recover@example.test',password='OriginalIsolated!729')
        response=self.client.post('/accounts/password-reset/',{'email':user.email})
        self.assertRedirects(response,'/accounts/password-reset/done/');self.assertEqual(len(mail.outbox),1)
        link=re.search(r'https?://[^\s]+/accounts/reset/[^\s]+',mail.outbox[0].body).group(0)
        from urllib.parse import urlsplit
        response=self.client.get(urlsplit(link).path,follow=True)
        self.assertContains(response,'new_password1')
        response=self.client.post(response.request['PATH_INFO'],{'new_password1':'ReplacedIsolated!729','new_password2':'ReplacedIsolated!729'})
        self.assertRedirects(response,'/accounts/reset/done/')
        self.assertTrue(self.client.login(username=user.username,password='ReplacedIsolated!729'))

    def test_unassigned_feedback_cannot_be_reviewed_by_other_school_or_parent(self):
        old=Feedback.objects.create(kind='feedback',message='Private unassigned feedback')
        self.school.name='Other school';self.school.save()
        self.client.force_login(self.staff)
        self.assertNotContains(self.client.get('/staff/feedback/'),old.message)
        self.assertEqual(self.client.post(f'/staff/feedback/{old.pk}/',{'status':'resolved'}).status_code,404)
        self.client.force_login(self.parent)
        self.assertEqual(self.client.get('/staff/feedback/').status_code,403)
