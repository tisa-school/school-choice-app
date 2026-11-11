import json
from django.test import override_settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from playwright.sync_api import sync_playwright,expect

@override_settings(STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class DemoModerationBrowserTests(StaticLiveServerTestCase):
    def make_listing(self,page):
        page.goto(self.live_server_url+'/demo/creator/')
        for selector,value in [('#field-title','Supervised art workshop'),('#field-titlePt','Oficina de arte acompanhada'),('#description','A supervised English art workshop for ages 8–12.'),('#descriptionPt','Uma oficina de arte acompanhada.'),('#accessibility-en','Step-free access in this fictional venue.'),('#accessibility-pt','Acesso sem degraus no local fictício.')]:page.locator(selector).fill(value)
        page.locator('#field-minAge').fill('8');page.locator('#field-maxAge').fill('12')
        page.get_by_role('button',name='Preview activity',exact=True).click()
        page.get_by_role('dialog').get_by_role('button',name='Submit for review',exact=True).click()
    def test_automatic_check_persists_and_editing_invalidates_it(self):
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':390,'height':844});calls=[]
            def respond(route):
                calls.append(route.request.post_data_json)
                route.fulfill(status=200,content_type='application/json',body=json.dumps({'source':'ai','status':'safe','flags':[]}))
            page.route('**/demo/moderation-check/',respond)
            self.make_listing(page)
            page.locator('#role').select_option('admin')
            expect(page.locator('.moderation-advice .pill')).to_have_text('Safe')
            expect(page.locator('.moderation-advice')).to_contain_text('not verified child safety')
            self.assertEqual(len(calls),1);self.assertNotIn('requests',calls[0]['activity'])
            page.reload();expect(page.locator('.moderation-advice .pill')).to_have_text('Safe');self.assertEqual(len(calls),1)
            page.locator('#role').select_option('organizer')
            page.locator('.request-row',has_text='Supervised art workshop').get_by_role('link',name='Edit',exact=True).click()
            page.locator('#description').fill('A wine-tasting activity for ages 8–12.')
            page.unroute('**/demo/moderation-check/')
            page.route('**/demo/moderation-check/',lambda route:route.fulfill(status=200,content_type='application/json',body=json.dumps({'source':'ai','status':'needs_review','flags':[{'type':'risky_word','reason':'Review age-inappropriate wording about wine.'}]})))
            page.get_by_role('button',name='Preview activity',exact=True).click()
            page.get_by_role('dialog').get_by_role('button',name='Submit for review',exact=True).click()
            page.locator('#role').select_option('admin')
            expect(page.locator('.moderation-advice .pill')).to_have_text('Needs review')
            expect(page.locator('.moderation-advice')).to_contain_text('wine')
            self.assertFalse(page.evaluate('document.documentElement.scrollWidth>innerWidth'))
            # The advisory check cannot make the final decision or disable manual judgement.
            page.get_by_role('button',name='Reject example',exact=True).click()
            expect(page.locator('.moderation-advice')).to_have_count(0)
            browser.close()
    def test_missing_ai_retains_review_label_and_admin_can_decide(self):
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            page=browser.new_page();self.make_listing(page);page.locator('#role').select_option('admin')
            expect(page.locator('.moderation-advice .pill')).to_have_text('Needs review')
            expect(page.locator('.moderation-advice')).to_contain_text('AI screening is unavailable')
            page.get_by_role('button',name='Approve example',exact=True).click()
            expect(page.locator('.moderation-advice')).to_have_count(0)
            if page.locator('.nav-menu-toggle').is_visible() and not page.locator('.product-sidebar').is_visible():page.locator('.nav-menu-toggle').click()
            page.locator('nav [data-view="events"]').click()
            expect(page.get_by_role('heading',name='Supervised art workshop',exact=True)).to_be_visible()
            browser.close()
