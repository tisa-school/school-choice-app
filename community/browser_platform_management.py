from io import BytesIO
from PIL import Image
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.auth.models import User
from django.test import override_settings
from playwright.sync_api import sync_playwright,expect
from .models import School,Membership,TeamPhoto

@override_settings(STORAGES={'default':{'BACKEND':'community.storage.DatabasePrivateStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class PlatformManagementBrowserTests(StaticLiveServerTestCase):
    def test_real_sign_in_daniel_crop_replace_and_private_persistence(self):
        school=School.objects.create(name='Unicorn School',invite_code_hash='private')
        admin=User.objects.create_user('existing-non-email-username',email='admin@isolated.test',password='IsolatedBrowserAdmin!729')
        Membership.objects.create(user=admin,school=school,role='staff',verified=True)
        out=BytesIO();Image.new('RGB',(600,450),'purple').save(out,'JPEG')
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce')
            page.goto(self.live_server_url+'/accounts/login/?next=/manage/')
            page.locator('#id_username').fill(admin.email);page.locator('#id_password').fill('IsolatedBrowserAdmin!729');page.get_by_role('button',name='Log In ✦',exact=True).click()
            page.wait_for_url('**/manage/');page.goto(self.live_server_url+'/manage/team/student-3/')
            expect(page.locator('h1')).to_have_text('Daniel Vinnikov')
            for _ in range(2):
                page.locator('[data-crop-file]').set_input_files({'name':'portrait.jpg','mimeType':'image/jpeg','buffer':out.getvalue()})
                expect(page.locator('canvas')).to_be_visible()
                page.locator('[data-crop-axis="zoom"]').evaluate("e=>{e.value='1.5';e.dispatchEvent(new Event('input',{bubbles:true}));}")
                page.get_by_role('button',name='Save photo',exact=True).click()
                expect(page.locator('[data-upload-status]')).to_contain_text('Team photo saved.')
                expect(page.locator('.team-portrait')).to_be_visible()
            page.reload();expect(page.locator('.team-portrait')).to_be_visible()
            source=page.locator('.team-portrait').get_attribute('src')
            page.screenshot(path='/tmp/tkzone-admin-daniel-editor.png',full_page=True)
            page.context.clear_cookies();self.assertEqual(page.request.get(self.live_server_url+source).status,404)
            page.goto(self.live_server_url+'/accounts/login/?next=/manage/team/student-3/')
            page.locator('#id_username').fill(admin.email);page.locator('#id_password').fill('IsolatedBrowserAdmin!729');page.get_by_role('button',name='Log In ✦',exact=True).click()
            expect(page.locator('.team-portrait')).to_be_visible()
            page.get_by_role('button',name='Delete photo',exact=True).click();expect(page.locator('.team-portrait')).to_have_count(0)
            browser.close()
        self.assertEqual(TeamPhoto.objects.count(),0)
