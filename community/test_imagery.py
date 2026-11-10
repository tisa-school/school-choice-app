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

    def matched_event(self):
        self.event.title='Watercolour drawing workshop'
        self.event.description='Draw a Lisbon-inspired city with watercolours.'
        self.event.venue='Alfama arts studio';self.event.area='Alfama'
        self.event.activity_environment='indoor';self.event.save()

    def test_live_activity_cover_and_reviewed_upload_priority(self):
        self.matched_event()
        response=self.client.get(f'/events/{self.event.pk}/')
        self.assertContains(response,'AI illustration · not this event')
        self.assertContains(response,'activity-drawing-768.')
        self.assertNotContains(response,'lisbon-rooftops-768.')
        self.event.image='events/existing-organiser-image.jpg';self.event.save()
        self.assertNotContains(self.client.get(f'/events/{self.event.pk}/'),f'/media/event/{self.event.pk}/')
        self.event.image_alt='Children drawing with watercolours at an indoor studio table.'
        self.event.image_source='stock';self.event._review_event_image=True;self.event.save()
        response=self.client.get(f'/events/{self.event.pk}/')
        self.assertContains(response,f'/media/event/{self.event.pk}/')
        self.assertContains(response,'Illustrative stock image · not this event')
        self.assertNotContains(self.client.get('/community/'),'Private school test event')

    def test_portuguese_cover_disclosure_and_demo_manifest(self):
        self.matched_event()
        self.assertContains(self.client.get(f'/events/{self.event.pk}/?lang=pt-PT'),'Ilustração IA')
        self.assertContains(self.client.get('/demo/'),'activity_imagery')
        self.assertContains(self.client.get('/demo/'),'activity-football-768.')

    def test_bundled_image_dimensions_and_card_weight(self):
        root=settings.BASE_DIR/'static/community/imagery'
        with Image.open(root/'tk-zone-share.png') as image:self.assertEqual(image.size,(1200,630));self.assertEqual(image.format,'PNG')
        from .activity_imagery import specification
        for scene in specification()['scenes'].values():
            stem=scene['file']
            path=root/f'{stem}-768.webp'
            with Image.open(path) as image:self.assertEqual(image.width,768);self.assertEqual(image.format,'WEBP')
            self.assertLess(path.stat().st_size,200000)
