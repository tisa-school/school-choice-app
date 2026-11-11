import json,re,tempfile
from io import BytesIO
from PIL import Image
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase,Client,override_settings
from . import test_features as fixtures
from .models import TeamPhoto,School
from .community_forms import clean_photo
from .localization import ACTIVE_LOCALES,catalog

@override_settings(MEDIA_ROOT=tempfile.gettempdir()+'/tkzone-about-portraits')
class AboutRefreshTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.FeatureTests.setUpTestData.__func__(cls)
        cls.school.name='Unicorn School';cls.school.save()
    def portrait(self,**extra):
        data=BytesIO();Image.new('RGB',(40,50),'purple').save(data,'JPEG')
        fields={'school':self.school,'uploaded_by':self.staff,'name':'Zehra Yilmaz','description':'Project lead portrait','image':clean_photo(SimpleUploadedFile('test.jpg',data.getvalue(),content_type='image/jpeg'))}
        fields.update(extra);return TeamPhoto.objects.create(**fields)
    def test_private_about_portrait_visible_only_to_real_administrators(self):
        photo=self.portrait();url=f'/protected-photos/team/{photo.pk}/'
        self.assertNotContains(self.client.get('/about/'),url)
        self.assertNotContains(self.client.get('/demo/about/?role=admin'),url)
        self.client.force_login(self.staff)
        self.assertContains(self.client.get('/about/'),url,count=1)
        self.assertContains(self.client.get('/demo/about/'),url,count=1)
        self.assertEqual(self.client.get(url).status_code,200)
        self.client.logout();self.assertEqual(self.client.get(url).status_code,404)
    def test_about_student_names_include_requested_surnames(self):
        photo=self.portrait(name='Sophia Gateneo',is_student=True,visibility='public',sharing_permission=True,guardian_consent=True,description='Student portrait')
        response=self.client.get('/about/');self.assertContains(response,f'/protected-photos/team/{photo.pk}/',count=1)

        for name in ['Sophia Gatenyo','Rosie Markovska','Daniel Vinnikov']:
            self.assertContains(response,name)
            self.assertContains(self.client.get('/demo/about/'),name)
    def test_portrait_from_unrelated_school_is_not_attached(self):
        school=School.objects.create(name='Other school',invite_code_hash='test-hash')
        photo=self.portrait(school=school,visibility='public',sharing_permission=True)
        self.assertNotContains(self.client.get('/about/'),f'/protected-photos/team/{photo.pk}/')
    def test_no_visible_tech_week_and_audience_is_eight_to_sixteen(self):
        project=json.loads((settings.BASE_DIR/'content/project.json').read_text());self.assertEqual(project['age_range'],{'min':8,'max':16})
        for code in ACTIVE_LOCALES:
            response=Client().get('/about/',{'lang':code});self.assertEqual(response.status_code,200)
            body=re.sub(r'<script.*?</script>','',response.content.decode(),flags=re.S)
            self.assertNotRegex(body,r'(?i)tech[\s-]?week');self.assertNotRegex(re.sub(r'<[^>]+>','',body),r'7[^\d]{0,15}12')
            self.assertEqual(set(catalog(code)),set(catalog('en')))
        source=(settings.BASE_DIR/'static/community/demo.js').read_text()
        self.assertNotRegex(source,r'(?i)tech[\s-]?week');self.assertIn('credits.age_range.max',source)
        self.assertNotIn('7–12',source);self.assertIn('8–16',source)
