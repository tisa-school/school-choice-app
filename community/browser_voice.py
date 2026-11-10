import json
from django.test import override_settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from playwright.sync_api import sync_playwright,expect

FAKE_SPEECH="""window.speechInstances=[];window.SpeechRecognition=class {constructor(){window.speechInstances.push(this);}start(){this.started=true;}stop(){this.onend?.();}abort(){this.aborted=true;}};"""
@override_settings(STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class VoiceBrowserTests(StaticLiveServerTestCase):
    def test_speech_review_ai_results_and_permission_error(self):
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':390,'height':844});page.add_init_script(FAKE_SPEECH)
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(self.live_server_url+'/demo/events/')
            page.get_by_role('button',name='Voice search',exact=True).click()
            page.locator('#voice-dialog input[type=checkbox]').check()
            page.get_by_role('button',name='Start listening',exact=True).click()
            page.evaluate("()=>{const r=window.speechInstances.at(-1);r.onresult({results:[[{transcript:'I like drawing and football'}]]});r.onend();}")
            expect(page.locator('#voice-transcript')).to_have_value('I like drawing and football')
            from pathlib import Path
            from django.conf import settings
            page.screenshot(path=str(Path(settings.BASE_DIR)/'docs/screenshots/voice-search-review.png'),full_page=True)
            calls=[]
            def reply(route):
                calls.append(route.request.post_data_json)
                route.fulfill(status=200,content_type='application/json',body=json.dumps({'filters':{'category':'','categories':['Arts','Sports'],'age':'','language':'','area':'','day':'','period':'','price':''}}))
            page.route('**/demo/voice-filters/',reply)
            page.get_by_role('button',name='Search with AI',exact=True).click()
            expect(page.locator('#voice-dialog')).not_to_be_visible()
            expect(page.locator('.event-card')).to_have_count(3)
            self.assertEqual(calls,[{'preferences':'I like drawing and football','consent':True}])
            page.reload();expect(page.locator('.event-card')).to_have_count(3)
            page.get_by_role('button',name='Voice search',exact=True).click();page.locator('#voice-dialog input[type=checkbox]').check()
            page.get_by_role('button',name='Start listening',exact=True).click()
            page.evaluate("()=>window.speechInstances.at(-1).onerror({error:'not-allowed'})")
            expect(page.locator('[data-voice-status]')).to_contain_text('permission was denied')
            page.get_by_role('button',name='Cancel',exact=True).click()
            self.assertTrue(page.evaluate('window.speechInstances.at(-1).aborted'))
            self.assertFalse(page.evaluate('document.documentElement.scrollWidth>innerWidth'))
            self.assertEqual(errors,[]);browser.close()
    def test_unsupported_browser_keeps_typed_search(self):
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            page=browser.new_page();page.add_init_script('window.SpeechRecognition=undefined;window.webkitSpeechRecognition=undefined;')
            page.goto(self.live_server_url+'/demo/events/')
            expect(page.locator('[data-voice-hint]')).to_contain_text('not supported')
            page.get_by_role('button',name='Voice search',exact=True).click()
            expect(page.get_by_role('button',name='Start listening',exact=True)).to_be_disabled()
            page.get_by_role('button',name='Cancel',exact=True).click()
            page.get_by_label('Search activities',exact=True).fill('Creative Art')
            page.get_by_role('button',name='Search',exact=True).click()
            expect(page.locator('.event-card')).to_have_count(1)
            browser.close()
    def test_live_voice_search_submits_reviewed_text_to_finder(self):
        from unittest.mock import patch
        with patch('community.finder.interpret',return_value={'category':'Arts'}):
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
                page=browser.new_page();page.add_init_script(FAKE_SPEECH)
                page.goto(self.live_server_url+'/community/')
                page.get_by_role('button',name='Voice search',exact=True).click()
                page.locator('#voice-dialog input[type=checkbox]').check()
                page.locator('#voice-transcript').fill('I like drawing')
                page.get_by_role('button',name='Search with AI',exact=True).click()
                page.wait_for_url('**/finder/')
                expect(page.locator('#preferences')).to_have_value('I like drawing')
                self.assertEqual(page.get_by_text('CSRF verification failed.',exact=False).count(),0)
                browser.close()
