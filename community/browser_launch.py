"""Browser coverage for live discovery and staff publication controls, with isolated data."""
import os,shutil,tempfile
from io import BytesIO
from PIL import Image
from playwright.sync_api import sync_playwright,expect
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from . import test_features as fixtures

@override_settings(STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}},MEDIA_ROOT=tempfile.gettempdir()+'/tkzone-launch-browser',AI_API_KEY='')
class LaunchBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        fixtures.FeatureTests.setUpTestData.__func__(type(self))
        self.school.name='Unicorn School';self.school.save()
    def test_live_discovery_portrait_publication_and_school_access(self):
        image=BytesIO();Image.new('RGB',(100,130),'purple').save(image,'JPEG')
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=os.getenv('BROWSER_EXECUTABLE') or shutil.which('chromium'),args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':390,'height':844});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(self.live_server_url+'/?lang=en')
            expect(page.get_by_role('heading',name='Discover. Connect. Belong.',exact=True)).to_be_visible()
            self.assertNotRegex(page.locator('body').inner_text(),r'(?i)demo|simulated|fictional')
            expect(page.get_by_role('heading',name=self.event.title,exact=True)).to_be_visible()
            page.goto(self.live_server_url+'/finder/?search=1&category=Arts&age=11&language=en')
            expect(page.get_by_role('heading',name=self.event.title,exact=True)).to_be_visible()
            page.goto(self.live_server_url+'/accounts/login/?lang=en')
            page.locator('#id_username').fill('staff@example.test');page.locator('#id_password').fill('FamilyTesting!729')
            page.get_by_role('button',name='Log In',exact=False).click();page.wait_for_load_state()
            page.goto(self.live_server_url+'/about/?lang=en')
            form=page.locator('[data-person="student-1"]')
            expect(form.locator('.form-save-status')).to_have_count(0)
            form.locator('input[type=file]').set_input_files({'name':'portrait.jpg','mimeType':'image/jpeg','buffer':image.getvalue()})
            form.get_by_role('button',name='Save photo',exact=True).click()
            expect(form.locator('[data-upload-status]')).to_have_text('Team photo saved.')
            portrait=form.locator('xpath=..').locator('img.team-portrait');url=portrait.get_attribute('src').split('?')[0]
            guest=browser.new_context();self.assertEqual(guest.request.get(self.live_server_url+url).status,404)
            form.get_by_role('button',name='Publish photo',exact=True).click()
            expect(form.locator('[data-upload-status]')).to_have_text('Confirm permission before sharing photos.')
            form.locator('[name=publish_consent]').check();form.get_by_role('button',name='Publish photo',exact=True).click()
            expect(form.locator('[data-photo-visibility]')).to_have_text('Public')
            self.assertEqual(guest.request.get(self.live_server_url+url).status,200)
            for width in [390,768,1440]:
                page.set_viewport_size({'width':width,'height':1000});self.assertFalse(page.evaluate('document.documentElement.scrollWidth>innerWidth'))
            page.reload();expect(page.locator('[data-person="student-1"] [data-photo-visibility]')).to_have_text('Public')
            form=page.locator('[data-person="student-1"]');form.get_by_role('button',name='Make private',exact=True).click()
            expect(form.locator('[data-photo-visibility]')).to_have_text('Administrators only')
            self.assertEqual(guest.request.get(self.live_server_url+url).status,404)
            page.route('**/team/portraits/student-1/',lambda route:route.fulfill(status=503,content_type='text/html',body='<h1>Unavailable</h1>'))
            form.locator('[name=publish_consent]').check();form.get_by_role('button',name='Publish photo',exact=True).click()
            expect(form.locator('[data-upload-status]')).to_have_text('Please refresh the page and try again.')
            expect(form.get_by_role('button',name='Publish photo',exact=True)).to_be_enabled()
            page.unroute('**/team/portraits/student-1/')
            page.goto(self.live_server_url+'/staff/school/?lang=en')
            page.locator('#id_code').fill('New-isolated-school-code!');page.locator('#id_password').fill('FamilyTesting!729')
            page.get_by_role('button',name='Save changes',exact=False).click()
            expect(page.locator('.messages').get_by_text('School invite code updated.',exact=True)).to_be_visible()
            self.assertNotIn('New-isolated-school-code!',page.content())
            self.assertFalse(errors,errors);browser.close()
