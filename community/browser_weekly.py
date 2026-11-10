import json
from unittest.mock import patch
from django.test import override_settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from playwright.sync_api import sync_playwright,expect

@override_settings(STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class WeeklyBrowserTests(StaticLiveServerTestCase):
    def test_summary_updates_after_decisions_refresh_and_reset(self):
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':390,'height':844})
            page.goto(self.live_server_url+'/demo/events/art-afternoon/')
            page.get_by_role('button',name='Ask mum or dad ✦',exact=True).click()
            page.locator('#role').select_option('parent')
            expect(page.locator('.weekly-facts')).to_contain_text('1 activity; 0 approved')
            page.get_by_role('button',name='Approve',exact=True).click()
            expect(page.locator('.weekly-facts')).to_contain_text('1 activity; 1 approved')
            expect(page.locator('.weekly-next')).to_contain_text('Little Discoveries Lab')
            page.locator('nav [data-view="events"]').click()
            page.locator('[data-view="detail"][data-id="math-makers"]').first.click()
            page.get_by_role('button',name='Ask mum or dad ✦',exact=True).click()
            page.locator('#role').select_option('parent')
            expect(page.locator('.weekly-facts')).to_contain_text('2 activities; 1 approved')
            from pathlib import Path
            from django.conf import settings
            expect(page.locator('#demo-feedback')).to_be_empty(timeout=8000)
            page.locator('.weekly-summary').screenshot(path=str(Path(settings.BASE_DIR)/'docs/screenshots/weekly-summary.png'))
            page.reload();expect(page.locator('.weekly-facts')).to_contain_text('2 activities; 1 approved')
            for width in [360,390,768,1440]:
                page.set_viewport_size({'width':width,'height':900})
                self.assertFalse(page.evaluate('document.documentElement.scrollWidth>innerWidth'))
            page.get_by_role('button',name='Reset demo',exact=True).click()
            page.get_by_role('dialog').get_by_role('button',name='Confirm',exact=True).click()
            page.locator('#role').select_option('parent')
            expect(page.locator('.weekly-facts')).to_contain_text('0 activities; 0 approved')
            browser.close()
    @override_settings(ANTHROPIC_API_KEY='test-only-key')
    def test_real_ai_badge_only_after_success_and_no_counts_invented(self):
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            page=browser.new_page();calls=[]
            def reply(route):
                calls.append(route.request.post_data_json)
                route.fulfill(status=200,content_type='application/json',body=json.dumps({'source':'ai','commentary':'A little curiosity can open the door to your next shared adventure.'}))
            page.route('**/demo/weekly-summary/',reply)
            page.goto(self.live_server_url+'/demo/family/')
            expect(page.locator('#weekly-comment')).to_contain_text('AI weekly summary')
            expect(page.locator('.weekly-facts')).to_contain_text('0 activities; 0 approved')
            self.assertEqual(set(calls[0]),{'requested','approved','period','locale'})
            page.unroute('**/demo/weekly-summary/')
            page.route('**/demo/weekly-summary/',lambda route:route.fulfill(status=503,content_type='application/json',body='{}'))
            page.reload()
            expect(page.locator('#weekly-comment')).to_contain_text('Factual overview')
            expect(page.locator('#weekly-comment')).not_to_contain_text('AI weekly summary')
            browser.close()
