import json
from django.test import override_settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from playwright.sync_api import sync_playwright,expect

@override_settings(STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class AIEffectsBrowserTests(StaticLiveServerTestCase):
    def test_glow_glass_hover_and_reduced_motion(self):
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':1440,'height':1000})
            page.goto(self.live_server_url+'/demo/')
            expect(page.locator('.hero')).to_have_attribute('data-ai-glow','animate')
            self.assertEqual(page.locator('.hero').evaluate("e=>getComputedStyle(e,'::before').animationName"),'ai-hero-glow')
            page.screenshot(path='/tmp/tkzone-ai-native-desktop.png',animations='disabled')
            page.locator('nav [data-view="events"]').click()
            self.assertIn('blur',page.locator('.event-card').first.evaluate('e=>getComputedStyle(e).backdropFilter'))
            page.locator('.event-card').first.hover()
            page.wait_for_function("() => getComputedStyle(document.querySelector('.event-card')).transform !== 'none'")
            page.emulate_media(reduced_motion='reduce')
            self.assertEqual(page.locator('.event-card').first.evaluate('e=>getComputedStyle(e).transform'),'none')
            page.locator('.product-brand').click()
            self.assertEqual(page.locator('.hero').evaluate("e=>getComputedStyle(e,'::before').animationName"),'none')
            for width in [360,390,768,1440]:
                page.set_viewport_size({'width':width,'height':900})
                for route in ['/demo/','/community/','/finder/']:
                    page.goto(self.live_server_url+route)
                    self.assertFalse(page.evaluate('document.documentElement.scrollWidth>innerWidth'),f'{route}, {width}')
            browser.close()
    @override_settings(ANTHROPIC_API_KEY='test-only-key')
    def test_complete_accessible_answer_typing_and_immediate_reduced_motion(self):
        answer='Art fits your interests and age group, with English available to make joining easier.'
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':1440,'height':1000})
            page.route('**/demo/ai-match/',lambda route:route.fulfill(status=200,content_type='application/json',body=json.dumps({'source':'ai','explanation':answer,'percentage':100,'age_eligible':True})))
            # Bring the completed answer into view before explicitly testing the visual reveal.
            page.goto(self.live_server_url+'/demo/events/art-afternoon/')
            expect(page.locator('#ai-match-content')).to_contain_text(answer)
            page.locator('#ai-match-content').scroll_into_view_if_needed()
            page.evaluate("()=>{window.TKAIEffects.finishAll();const n=document.querySelector('#ai-match-content p[data-user-content]');window.TKAIEffects.type(n,'test-accessible-answer');}")
            expect(page.locator('#ai-match-content .ai-complete-text')).to_have_text(answer)
            expect(page.locator('#ai-match-content .ai-visual-text')).to_have_attribute('aria-hidden','true')
            before=page.locator('#ai-match-content').bounding_box()['height']
            page.emulate_media(reduced_motion='reduce')
            expect(page.locator('#ai-match-content .ai-visual-text')).to_have_count(0)
            expect(page.locator('#ai-match-content')).to_contain_text(answer)
            self.assertAlmostEqual(before,page.locator('#ai-match-content').bounding_box()['height'],delta=2)
            self.assertEqual(page.locator('.ai-sparkle').first.evaluate('e=>getComputedStyle(e).animationName'),'none')
            # Cached answers and state rerenders do not restart a typing effect.
            page.locator('[data-demo-action="save"], [data-action="save"]').first.click()
            self.assertEqual(page.locator('.ai-typing').count(),0)
            browser.close()
