from urllib.parse import urlsplit
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from playwright.sync_api import sync_playwright, expect

@override_settings(STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class CityImageryBrowserTests(StaticLiveServerTestCase):
    def test_demo_images_detail_responsiveness_and_anonymous_social_image(self):
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce')
            page.goto(self.live_server_url+'/demo/events/')
            expect(page.locator('.event-card img.city-cover')).to_have_count(10)
            first=page.locator('.event-card img.city-cover').first
            first.scroll_into_view_if_needed()
            expect(first).to_have_attribute('alt','AI-generated illustration inspired by Lisbon rooftops and the Tagus')
            page.wait_for_function('Array.from(document.querySelectorAll(".event-card img")).slice(0,3).every(i=>i.complete&&i.naturalWidth>0)')
            for width in [390,768,1440]:
                page.set_viewport_size({'width':width,'height':1000})
                self.assertFalse(page.evaluate('document.documentElement.scrollWidth>innerWidth'))
            page.screenshot(path='/tmp/tkzone-city-discover.png',full_page=True)
            page.locator('.event-card .art').first.click()
            expect(page.locator('.detail-art img.city-cover')).to_be_visible()
            expect(page.locator('.detail-art .city-image-caption')).to_contain_text('not the venue')
            page.screenshot(path='/tmp/tkzone-city-detail.png')
            image=page.locator('meta[property="og:image"]').get_attribute('content')
            self.assertTrue(image.startswith('https://school-choice-app-hrvb.vercel.app/'))
            response=page.request.get(self.live_server_url+urlsplit(image).path)
            self.assertEqual(response.status,200);self.assertIn('image/png',response.headers['content-type'])
            self.assertEqual(response.body()[:8],b'\x89PNG\r\n\x1a\n')
            browser.close()
