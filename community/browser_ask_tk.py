import json
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from playwright.sync_api import sync_playwright, expect

@override_settings(STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class AskTKBrowserTests(StaticLiveServerTestCase):
    def test_browse_demo_privacy_keyboard_and_mobile(self):
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':390,'height':844},reduced_motion='reduce')
            page.goto(self.live_server_url+'/demo/')
            page.locator('#ask-tk-launcher').click()
            expect(page.locator('#tk-question')).to_be_focused()
            page.locator('[data-tk-browse]').click()
            expect(page.locator('#tk-reply article')).to_have_count(4)
            expect(page.locator('#tk-reply')).to_contain_text('AI was not used')
            page.locator('#tk-question').fill('private unsent text')
            page.keyboard.press('Escape')
            expect(page.locator('#ask-tk-launcher')).to_be_focused()
            page.locator('#ask-tk-launcher').click()
            expect(page.locator('#tk-question')).to_have_value('')
            expect(page.locator('#tk-reply')).to_be_empty()
            self.assertFalse(page.evaluate('document.documentElement.scrollWidth>innerWidth'))
            box=page.locator('#ask-tk-panel').bounding_box()
            self.assertGreaterEqual(box['x'],0);self.assertLessEqual(box['y']+box['height'],844)
            page.screenshot(path='/tmp/tkzone-ask-tk-mobile.png')
            page.reload()
            expect(page.locator('#ask-tk-panel')).not_to_be_visible()
            for path in ['/community/','/finder/','/about/']:
                page.goto(self.live_server_url+path)
                expect(page.locator('#ask-tk-launcher')).to_be_visible()
            browser.close()

    def test_ai_suggestions_from_current_demo_state_and_error_fallback(self):
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce')
            page.route('**/assistant/ask/',lambda route:route.fulfill(status=200,content_type='application/json',body=json.dumps({'source':'ai','filters':{'category':'Arts','age':'11','language':'en'},'days':['2026-11-14','2026-11-15'],'results':[]})))
            page.goto(self.live_server_url+'/demo/')
            page.locator('#ask-tk-launcher').click()
            page.locator('#tk-question').fill('English art this weekend for age 11')
            page.locator('#tk-consent').check()
            page.locator('#tk-chat-form button').click()
            expect(page.locator('#tk-reply article')).to_have_count(1)
            expect(page.locator('#tk-reply article a')).to_have_text('Creative Art Afternoon')
            page.unroute('**/assistant/ask/')
            page.route('**/assistant/ask/',lambda route:route.fulfill(status=503,content_type='application/json',body='{"error":"unavailable"}'))
            page.locator('#tk-question').fill('Science')
            page.locator('#tk-consent').check()
            page.locator('#tk-chat-form button').click()
            expect(page.locator('#tk-reply')).to_contain_text('AI is unavailable')
            expect(page.locator('[data-tk-browse]')).to_be_enabled()
            page.keyboard.press('Escape')
            page.goto(self.live_server_url+'/demo/?lang=pt-PT')
            page.locator('#ask-tk-launcher').click()
            expect(page.locator('#ask-tk-title')).to_contain_text('Pergunta ao TK')
            browser.close()
