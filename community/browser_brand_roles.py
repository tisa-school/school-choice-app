from django.contrib.auth.models import User
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from django.conf import settings
from playwright.sync_api import sync_playwright, expect
from .models import School, Membership, ParentAccount


@override_settings(STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class BrandRoleBrowserTests(StaticLiveServerTestCase):
    def test_guest_role_visibility_navigation_guards_and_about_palette(self):
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':1440,'height':1100},reduced_motion='reduce')
            page.goto(self.live_server_url+'/demo/')
            expect(page.locator('nav [data-view="organizer"]')).to_have_count(0)
            page.evaluate("()=>{const a=document.createElement('a');a.dataset.view='organizer';document.body.append(a);a.click();a.remove();}")
            expect(page.locator('#role')).to_have_value('child')
            expect(page.locator('#demo-app')).not_to_have_attribute('data-screen','organizer')
            self.assertEqual(page.locator('.city-art').evaluate('e=>getComputedStyle(e).backgroundColor'),'rgb(68, 12, 176)')
            self.assertEqual(page.locator('.sun').evaluate('e=>getComputedStyle(e).color'),'rgb(255, 107, 0)')
            page.locator('#role').select_option('parent')
            expect(page.locator('nav [data-view="organizer"]')).to_have_count(0)
            page.locator('#role').select_option('organizer')
            expect(page.locator('#demo-app')).to_have_attribute('data-screen','organizer')
            page.locator('#role').select_option('child')
            page.goto(self.live_server_url+'/demo/about/')
            expect(page.locator('#demo-app')).to_contain_text('Sophia Gatenyo')
            self.assertEqual(page.locator('#demo-app>.story-band').evaluate('e=>getComputedStyle(e).backgroundColor'),'rgb(68, 12, 176)')
            page.screenshot(path='/tmp/tkzone-brand-demo-about.png',full_page=True)
            page.goto(self.live_server_url+'/about/')
            self.assertEqual(page.locator('.mission-panel').first.evaluate('e=>getComputedStyle(e).backgroundColor'),'rgb(68, 12, 176)')
            page.screenshot(path='/tmp/tkzone-brand-about.png',full_page=True)
            for width in [390,768,1440]:
                page.set_viewport_size({'width':width,'height':1000})
                for path in ['/about/','/demo/about/','/demo/','/community/']:
                    page.goto(self.live_server_url+path)
                    self.assertFalse(page.evaluate('document.documentElement.scrollWidth>innerWidth'),f'{width}, {path}')
            browser.close()

    def test_signed_in_parent_cannot_switch_demo_into_organiser(self):
        user=User.objects.create_user('role-bound-parent@test.invalid')
        ParentAccount.objects.create(user=user)
        self.client.force_login(user)
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            context=browser.new_context()
            context.add_cookies([{'name':settings.SESSION_COOKIE_NAME,'value':self.client.cookies[settings.SESSION_COOKIE_NAME].value,'url':self.live_server_url}])
            page=context.new_page();page.goto(self.live_server_url+'/demo/')
            expect(page.locator('#role option')).to_have_count(1)
            expect(page.locator('#role')).to_have_value('parent')
            expect(page.locator('#role')).to_be_disabled()
            expect(page.locator('nav [data-view="organizer"]')).to_have_count(0)
            response=page.goto(self.live_server_url+'/demo/organizer/?role=organizer')
            self.assertEqual(response.status,403)
            browser.close()
