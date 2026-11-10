from pathlib import Path
from django.conf import settings
from django.test import TestCase, override_settings
from PIL import Image
from . import test_features as fixtures

class ImageryTests(TestCase):
    @classmethod
    def setUpTestData(cls):fixtures.FeatureTests.setUpTestData.__func__(cls)

    def test_guest_metadata_is_absolute_server_rendered_and_generic(self):
        for path in ['/','/demo/','/community/','/finder/','/accounts/login/']:
            response=self.client.get(path)
            self.assertContains(response,'property="og:image"')
            self.assertContains(response,'content="1200"')
            self.assertContains(response,'content="630"')
            self.assertContains(response,'https://school-choice-app-hrvb.vercel.app/static/community/imagery/tk-zone-share.')
            self.assertContains(response,'summary_large_image')
            self.assertNotContains(response,'Other private child')

    @override_settings(PUBLIC_SITE_URL='https://school.example')
    def test_metadata_uses_configured_origin_not_request_host_or_query(self):
        response=self.client.get('/demo/?secret=never-share-this')
        self.assertContains(response,'https://school.example/static/community/imagery/tk-zone-share.')
        self.assertNotContains(response,'never-share-this')
        self.assertNotContains(response,'http://testserver/static/community/imagery')

    def test_live_cover_fallback_and_uploaded_image_priority(self):
        response=self.client.get(f'/events/{self.event.pk}/')
        self.assertContains(response,'AI city scene · not the venue')
        self.assertContains(response,'lisbon-rooftops-768.')
        self.assertContains(response,'srcset=')
        self.event.image='events/existing-organiser-image.jpg';self.event.save()
        response=self.client.get(f'/events/{self.event.pk}/')
        self.assertContains(response,f'/media/event/{self.event.pk}/')
        self.assertNotContains(response,'AI city scene · not the venue')
        self.assertNotContains(self.client.get('/community/'),'Private school test event')

    def test_portuguese_cover_disclosure_and_demo_manifest(self):
        response=self.client.get(f'/events/{self.event.pk}/?lang=pt-PT')
        self.assertContains(response,'Imagem da cidade gerada por IA')
        self.assertContains(self.client.get('/demo/'),'activity_imagery')
        self.assertContains(self.client.get('/demo/'),'lisbon-riverside-768.')

    def test_bundled_image_dimensions_and_card_weight(self):
        root=settings.BASE_DIR/'static/community/imagery'
        with Image.open(root/'tk-zone-share.png') as image:self.assertEqual(image.size,(1200,630));self.assertEqual(image.format,'PNG')
        for stem in ['lisbon-rooftops','lisbon-riverside']:
            path=root/f'{stem}-768.webp'
            with Image.open(path) as image:self.assertEqual(image.width,768);self.assertEqual(image.format,'WEBP')
            self.assertLess(path.stat().st_size,200000)
