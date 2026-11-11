from io import BytesIO
from importlib import import_module
from django.test import TestCase, override_settings
from django.apps import apps
from django.db import connection
from PIL import Image
from .models import SchoolProfile

class DeviceDirectoryTests(TestCase):
    @override_settings(PUBLIC_SITE_URL='https://schools.example')
    def test_qr_destinations_are_fixed_and_public(self):
        response=self.client.get('/test/?target=schools',HTTP_HOST='testserver')
        self.assertContains(response,'https://schools.example/schools/')
        self.assertContains(response,'Download QR code')
        self.assertNotContains(response,'testserver/schools/')
        for target in ['schools','demo','preview']:
            response=self.client.get('/test/qr.png',{'target':target})
            self.assertEqual(response.status_code,200)
            self.assertEqual(response['Content-Type'],'image/png')
            image=Image.open(BytesIO(response.content));self.assertEqual(image.format,'PNG')
            self.assertGreaterEqual(image.width,290)
        self.assertEqual(self.client.get('/test/qr.png?target=https://evil.example').status_code,404)
        self.assertEqual(self.client.get('/test/?target=https://evil.example').context['test_target'],'schools')
        self.assertContains(self.client.get('/test/?target=preview'),'requires Vercel sign-in')

    def test_source_seed_is_idempotent_and_does_not_overwrite(self):
        module=import_module('community.migrations.0015_expand_sourced_directory')
        count=SchoolProfile.objects.count()
        item=SchoolProfile.objects.get(slug='united-lisbon-international-school')
        item.summary='School staff correction';item.save()
        from types import SimpleNamespace
        module.add_profiles(apps,SimpleNamespace(connection=connection))
        self.assertEqual(SchoolProfile.objects.count(),count)
        item.refresh_from_db();self.assertEqual(item.summary,'School staff correction')
        for record in module.PROFILES:
            profile=SchoolProfile.objects.get(slug=record['slug'])
            self.assertTrue(profile.source_url.startswith('https://'))
            self.assertIsNone(profile.annual_fee_from)
            profile.full_clean()

    def test_city_and_sort_filter_exclude_drafts_and_keep_unknown_fees_last(self):
        SchoolProfile.objects.create(slug='test-expensive',name='Test expensive',city='Test town',annual_fee_from=9000,is_published=True)
        SchoolProfile.objects.create(slug='test-cheap',name='Test cheap',city='Test town',annual_fee_from=5000,is_published=True)
        SchoolProfile.objects.create(slug='test-unknown',name='Test unknown',city='Test town',is_published=True)
        SchoolProfile.objects.create(slug='test-draft',name='Test draft',city='Test town')
        response=self.client.get('/schools/',{'city':'test TOWN','sort':'fee'})
        self.assertEqual([p.slug for p in response.context['school_results']],['test-cheap','test-expensive','test-unknown'])
        response=self.client.get('/schools/',{'city':'Test town','sort':'name_desc'})
        self.assertEqual([p.slug for p in response.context['school_results']],['test-unknown','test-expensive','test-cheap'])
        self.assertFalse(self.client.get('/schools/?sort=invalid').context['school_results'])
        self.assertContains(self.client.get('/test/?lang=pt-PT'),'Testar no telemóvel')
