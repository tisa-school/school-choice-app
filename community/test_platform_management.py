import tempfile
from io import BytesIO
from PIL import Image
from django.test import TestCase,Client,override_settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import School,Membership,TeamPhoto,PlatformAudit,SiteConfiguration

@override_settings(MEDIA_ROOT=tempfile.gettempdir()+'/tk-platform-management-tests')
class PlatformManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school=School.objects.create(name='Unicorn School',invite_code_hash='private')
        cls.staff=User.objects.create_user('existing-admin-username',email='administrator@example.test',password='IsolatedAdminTest!729')
        Membership.objects.create(user=cls.staff,school=cls.school,role='staff',verified=True)
        cls.other=User.objects.create_user('other-parent',password='OtherIsolatedTest!729')
    def image(self):
        out=BytesIO();Image.new('RGB',(80,100),'purple').save(out,'JPEG');return SimpleUploadedFile('portrait.jpg',out.getvalue(),content_type='image/jpeg')
    def test_existing_admin_can_login_by_email_without_django_staff_flag(self):
        response=self.client.post('/accounts/login/?next=/manage/',{'username':'ADMINISTRATOR@example.test','password':'IsolatedAdminTest!729'})
        self.assertEqual(response.status_code,302);self.assertEqual(self.client.get('/manage/').status_code,200)
        self.staff.refresh_from_db();self.assertFalse(self.staff.is_staff);self.assertFalse(self.staff.is_superuser)
        self.client.logout();self.assertEqual(self.client.get('/manage/').status_code,302)
    def test_ambiguous_email_does_not_choose_an_account(self):
        User.objects.create_user('second-admin',email=self.staff.email,password='IsolatedAdminTest!729')
        self.assertFalse(self.client.login(username=self.staff.email,password='IsolatedAdminTest!729'))
    def test_existing_backend_sessions_are_preserved(self):
        self.client.force_login(self.staff,backend='django.contrib.auth.backends.ModelBackend')
        self.assertEqual(self.client.get('/manage/').status_code,200)
    def test_parent_and_unverified_staff_cannot_manage(self):
        self.client.force_login(self.other);self.assertEqual(self.client.get('/manage/').status_code,403)
        self.client.force_login(self.staff);Membership.objects.filter(user=self.staff).update(verified=False)
        self.assertEqual(self.client.get('/manage/team/student-3/').status_code,403)
    def test_daniel_photo_crop_reuses_existing_row_and_stays_private(self):
        photo=TeamPhoto.objects.create(school=self.school,uploaded_by=self.staff,name='Daniel Vinnikov',role='Student Contributors',is_student=True,image=self.image(),description='Daniel')
        self.assertTrue(self.client.login(username=self.staff.email,password='IsolatedAdminTest!729'))
        self.assertContains(self.client.get('/manage/team/student-3/'),'Daniel Vinnikov')
        for _ in range(2):
            response=self.client.post('/team/portraits/student-3/',{'image':self.image(),'crop_x':.3,'crop_y':.6,'crop_zoom':1.5},HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            self.assertEqual(response.status_code,200)
        self.assertEqual(TeamPhoto.objects.count(),1);photo.refresh_from_db();self.assertEqual(photo.pk,TeamPhoto.objects.get().pk)
        self.assertEqual(photo.visibility,'private');self.assertFalse(photo.guardian_consent)
        with photo.image.open() as stream:
            image=Image.open(stream);self.assertEqual(image.width,image.height)
        url=response.json()['url'];self.assertEqual(self.client.get(url).status_code,200)
        self.client.logout();self.assertEqual(self.client.get(url).status_code,404)
        self.client.login(username=self.staff.email,password='IsolatedAdminTest!729');self.assertEqual(self.client.get(url).status_code,200)
        self.assertTrue(PlatformAudit.objects.filter(action='portrait.updated',entity_id=str(photo.pk)).exists())
    def test_trusted_school_binding_supports_legacy_internal_school_name(self):
        self.school.name='Legacy internal school';self.school.save();SiteConfiguration.objects.create(project_school=self.school)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.post('/team/portraits/student-3/',{'image':self.image()},HTTP_X_REQUESTED_WITH='XMLHttpRequest').status_code,200)
        self.assertEqual(TeamPhoto.objects.get().school_id,self.school.pk)
    def test_school_admin_cannot_edit_other_school_records(self):
        other=School.objects.create(name='Other school',invite_code_hash='private');user=User.objects.create_user('outside');Membership.objects.create(user=user,school=other,role='parent')
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(f'/manage/records/users/{user.pk}/').status_code,404)
        self.assertEqual(self.client.get('/manage/settings/').status_code,403)
    def test_existing_username_sign_in_without_email_is_preserved(self):
        user=User.objects.create_user('trusted-legacy-name',password='LegacyIsolated!729')
        Membership.objects.create(user=user,school=self.school,role='staff',verified=True)
        response=self.client.post('/accounts/login/?next=/manage/',{'username':user.username,'password':'LegacyIsolated!729'})
        self.assertEqual(response.status_code,302);self.assertEqual(self.client.get('/manage/').status_code,200)
    def test_tiny_portrait_crop_is_valid_and_storage_error_is_not_success(self):
        from unittest.mock import patch
        self.client.force_login(self.staff)
        image=BytesIO();Image.new('RGB',(1,1),'purple').save(image,'PNG')
        response=self.client.post('/team/portraits/student-3/',{'image':SimpleUploadedFile('one.png',image.getvalue(),content_type='image/png'),'crop_x':0,'crop_y':0,'crop_zoom':3},HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code,200)
        with patch('django.core.files.storage.FileSystemStorage._save',side_effect=OSError('isolated storage failure')):
            response=self.client.post('/team/portraits/student-3/',{'image':self.image()},HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code,503);self.assertIn('could not be saved',response.json()['error'])
