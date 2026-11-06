from io import BytesIO
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from . import test_about_refresh
from django.test import TestCase,override_settings
import tempfile
from .models import TeamPhoto

@override_settings(MEDIA_ROOT=tempfile.gettempdir()+'/tkzone-inline-portraits')
class InlinePortraitTests(TestCase):
    setUpTestData=classmethod(test_about_refresh.AboutRefreshTests.setUpTestData.__func__)
    portrait=test_about_refresh.AboutRefreshTests.portrait
    def upload(self,person='student-1',**extra):
        data=BytesIO();Image.new('RGB',(30,40),'green').save(data,'JPEG')
        return self.client.post('/team/portraits/'+person+'/',{'image':SimpleUploadedFile('photo.jpg',data.getvalue(),content_type='image/jpeg'),**extra},HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    def test_controls_require_real_official_school_staff(self):
        self.assertNotContains(self.client.get('/about/'),'data-team-upload')
        self.assertNotContains(self.client.get('/demo/about/?role=admin'),'data-team-upload')
        self.client.force_login(self.staff)
        self.assertContains(self.client.get('/about/'),'data-team-upload',count=8)
        response=self.client.get('/demo/about/')
        self.assertContains(response,'data-team-upload',count=8)
        self.assertContains(response,'csrfmiddlewaretoken')
        self.school.name='Other school';self.school.save()
        self.assertNotContains(self.client.get('/about/'),'data-team-upload')
        self.assertEqual(self.upload().status_code,404)
    def test_upload_maps_canonical_person_and_stays_private(self):
        self.client.force_login(self.staff)
        response=self.upload(name='Wrong name',visibility='public',school=999)
        self.assertEqual(response.status_code,200)
        photo=TeamPhoto.objects.get()
        self.assertEqual(photo.name,'Sophia Gateneo');self.assertTrue(photo.is_student)
        self.assertEqual(photo.visibility,'private');self.assertFalse(photo.sharing_permission)
        body=self.client.get('/about/').content.decode()
        self.assertLess(body.index(response.json()['url']),body.index('<h3>Sophia Gateneo</h3>'))
        self.client.logout();self.assertEqual(self.client.get(response.json()['url']).status_code,404)
    def test_replacement_reuses_profile_and_revokes_old_sharing(self):
        photo=self.portrait(visibility='public',sharing_permission=True)
        self.client.force_login(self.staff)
        self.assertEqual(self.upload('lead').status_code,200)
        self.assertEqual(TeamPhoto.objects.count(),1)
        photo.refresh_from_db();self.assertEqual(photo.visibility,'private');self.assertFalse(photo.sharing_permission)
    def test_rejects_invalid_file_unknown_person_and_nonstaff(self):
        self.client.force_login(self.staff)
        response=self.client.post('/team/portraits/lead/',{'image':SimpleUploadedFile('bad.jpg',b'bad',content_type='image/jpeg')},HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code,400);self.assertFalse(TeamPhoto.objects.exists())
        self.assertEqual(self.upload('unknown').status_code,404)
        self.client.logout();self.assertEqual(self.upload().status_code,302)
    def test_post_requires_csrf(self):
        from django.test import Client
        client=Client(enforce_csrf_checks=True);client.force_login(self.staff)
        self.assertEqual(client.post('/team/portraits/lead/').status_code,403)

    def test_delete_removes_all_matching_portraits_only_in_own_school(self):
        from .models import School
        first=self.portrait();second=self.portrait()
        other_school=School.objects.create(name='Other school',invite_code_hash='test')
        other=self.portrait(school=other_school)
        student=self.portrait(name='Sophia Gateneo')
        self.client.force_login(self.staff)
        with self.captureOnCommitCallbacks(execute=True):
            response=self.client.post('/team/portraits/lead/',{'action':'delete'},HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code,200);self.assertTrue(response.json()['deleted'])
        self.assertFalse(TeamPhoto.objects.filter(pk__in=[first.pk,second.pk]).exists())
        self.assertFalse(first.image.storage.exists(first.image.name))
        self.assertTrue(TeamPhoto.objects.filter(pk=other.pk).exists())
        self.assertTrue(TeamPhoto.objects.filter(pk=student.pk).exists())
        self.assertNotContains(self.client.get('/about/'),f'/protected-photos/team/{first.pk}/')
        self.assertEqual(self.client.get(f'/protected-photos/team/{first.pk}/').status_code,404)
    def test_delete_requires_real_staff_and_csrf_and_is_idempotent(self):
        from django.test import Client
        photo=self.portrait()
        self.assertEqual(self.client.post('/team/portraits/lead/',{'action':'delete'}).status_code,302)
        client=Client(enforce_csrf_checks=True);client.force_login(self.staff)
        self.assertEqual(client.post('/team/portraits/lead/',{'action':'delete'}).status_code,403)
        self.client.force_login(self.staff)
        self.school.name='Other school';self.school.save()
        self.assertEqual(self.client.post('/team/portraits/lead/',{'action':'delete'}).status_code,404)
        self.assertTrue(TeamPhoto.objects.filter(pk=photo.pk).exists())
        self.school.name='Unicorn School';self.school.save()
        for _ in range(2):
            response=self.client.post('/team/portraits/lead/',{'action':'delete'})
            self.assertRedirects(response,'/about/#our-team')
