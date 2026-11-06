"""Browser walkthrough for language, registration, moderation and private photo workflows."""
from io import BytesIO
import tempfile
from PIL import Image
from playwright.sync_api import sync_playwright,expect
from django.test import override_settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from . import test_features as fixtures

@override_settings(STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}},MEDIA_ROOT=tempfile.gettempdir()+'/tkzone-browser-expansion')
class CommunityExpansionBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        fixtures.FeatureTests.setUpTestData.__func__(type(self))
        self.event.capacity=8;self.event.child_capacity=3;self.event.save()
    def test_language_attendance_moderation_and_photo_privacy(self):
        BASE=self.live_server_url
        image=BytesIO();Image.new('RGB',(80,80),'purple').save(image,'JPEG');upload={'name':'test.jpg','mimeType':'image/jpeg','buffer':image.getvalue()}
        def login(page,email):
            page.goto(BASE+'/accounts/login/?lang=en');page.locator('#id_username').fill(email);page.locator('#id_password').fill('FamilyTesting!729');page.locator('form').filter(has=page.locator('#id_password')).get_by_role('button',name='Log In',exact=False).first.click()
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);ctx=browser.new_context(viewport={'width':390,'height':844});page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            for locale in ['en','zh-CN','hi','es','ar','fr','bn','pt-PT','ru','ur']:
                response=page.goto(BASE+'/about/?lang='+locale);assert response.status==200
                assert page.locator('html').get_attribute('dir')==('rtl' if locale in ['ar','ur'] else 'ltr')
                assert page.locator('#interface-language option').count()>=10
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth'),locale
                assert page.get_by_role('heading',name='Sophia',exact=True).count()==1
            for width in [360,768,1440]:
                page.set_viewport_size({'width':width,'height':900})
                for locale in ['ar','ur']:
                    page.goto(BASE+'/about/?lang='+locale)
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth'),(width,locale)
            page.set_viewport_size({'width':390,'height':844})
            print('PASS: ten languages and mobile/tablet/desktop RTL/About layout',flush=True)
            page.goto(BASE+'/demo/?lang=en')
            for locale in ['ar','ur','zh-CN','fr','en']:
                page.locator('#language').select_option(locale);page.wait_for_function('(code)=>document.documentElement.lang===code',arg=locale)
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth'),('demo',locale)
            print('PASS: demo language switching and mobile layout',flush=True)
            login(page,'parent@example.test')
            response=page.goto(BASE+f'/events/{self.event.pk}/register/?lang=en');assert response.status==200
            page.locator('#id_adults').fill('2');page.locator('#id_children').fill('2');page.get_by_role('button',name='Send registration',exact=True).click();expect(page.get_by_role('heading',name='Family registrations',exact=True)).to_be_visible()
            print('PASS: family registration form',flush=True)
            page.goto(BASE+f'/events/{self.event.pk}/experiences/new/?lang=en');page.locator('#id_body').fill('A thoughtful supervised workshop.');page.locator('#id_photos').set_input_files([upload,upload]);page.locator('#id_photo_description').fill('A purple test image');page.locator('#id_permission').check();page.get_by_role('button',name='Submit for moderation',exact=True).click();expect(page.get_by_text('A thoughtful supervised workshop.',exact=True)).to_be_visible()
            print('PASS: parent comment and multiple photos saved for moderation',flush=True)
            staff=browser.new_page(viewport={'width':1440,'height':1000});login(staff,'staff@example.test');staff.goto(BASE+'/staff/content/?lang=en');staff.get_by_role('button',name='Publish contribution',exact=True).first.click()
            guest=browser.new_page();guest.goto(BASE+f'/events/{self.event.pk}/?lang=en');expect(guest.get_by_text('A thoughtful supervised workshop.',exact=True)).to_be_visible()
            staff.goto(BASE+f'/organizer/events/{self.event.pk}/?lang=en');staff.get_by_role('button',name='Confirm attendance',exact=True).click();staff.wait_for_load_state();assert staff.locator('.attendance-summary').last.inner_text().find('4')>=0
            print('PASS: moderation and group confirmation',flush=True)
            staff.goto(BASE+'/team/photos/new/?lang=en');staff.locator('#id_school').select_option(index=1);staff.locator('#id_name').fill('Student PrivateSurname');staff.locator('#id_is_student').check();staff.locator('#id_image').set_input_files(upload);staff.locator('#id_description').fill('A synthetic student portrait');staff.get_by_role('button',name='Save photo',exact=True).click();expect(staff.get_by_role('heading',name='Student',exact=True)).to_be_visible()
            photo_url=staff.locator('.photo-grid img').last.get_attribute('src');assert guest.request.get(BASE+photo_url).status==404
            guest.goto(BASE+'/team/photos/?lang=en');assert 'PrivateSurname' not in guest.locator('main').inner_text()
            print('PASS: administrator-only student photo and direct URL privacy',flush=True)
            assert not errors,errors;print('PASS: no browser runtime errors',flush=True);browser.close()
