from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from playwright.sync_api import sync_playwright,expect

@override_settings(STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class UnifiedSidebarBrowserTests(StaticLiveServerTestCase):
    def test_desktop_and_mobile_share_items_active_state_and_working_links(self):
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce');errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            for route in ['/','/schools/','/saved/','/community/','/finder/','/about/','/team/photos/','/events/','/activities/']:
                page.goto(self.live_server_url+route)
                nav=page.locator('.unified-navigation')
                links=nav.locator('a').evaluate_all('items=>items.map(a=>({key:a.dataset.navKey,href:a.getAttribute("href")}))')
                self.assertEqual(len(links),len({item['key'] for item in links}));self.assertEqual(len(links),len({item['href'] for item in links}))
                expect(nav.locator('[aria-current="page"]')).to_have_count(1)
                expect(page.locator('.community-tools,.sidebar-note,.bottom-nav')).to_have_count(0)
                if route=='/':
                    for link in links:
                        response=page.request.get(self.live_server_url+link['href']);self.assertLess(response.status,400,link)
                    page.screenshot(path='/tmp/tkzone-unified-sidebar-desktop.png')
                page.set_viewport_size({'width':390,'height':844})
                expect(nav).not_to_be_visible();toggle=page.get_by_role('button',name='Menu',exact=True);expect(toggle).to_be_visible();toggle.click();expect(toggle).to_have_attribute('aria-expanded','true')
                self.assertEqual(links,nav.locator('a').evaluate_all('items=>items.map(a=>({key:a.dataset.navKey,href:a.getAttribute("href")}))'))
                expect(nav).to_be_visible();self.assertFalse(page.evaluate('document.documentElement.scrollWidth>innerWidth'))
                if route=='/':page.screenshot(path='/tmp/tkzone-unified-sidebar-mobile.png',full_page=True)
                page.keyboard.press('Escape');expect(nav).not_to_be_visible();expect(toggle).to_be_focused()
                page.set_viewport_size({'width':1440,'height':1000})
            self.assertEqual(errors,[]);browser.close()
    def test_demo_uses_same_navigation_and_preserves_role_switches(self):
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':390,'height':844},reduced_motion='reduce')
            page.goto(self.live_server_url+'/demo/')
            for view in ['events','child','crews','calendar']:
                page.get_by_role('button',name='Menu',exact=True).click()
                nav=page.locator('.unified-navigation');expect(nav.locator('[aria-current="page"]')).to_have_count(1)
                expect(nav.locator('a[data-nav-key="saved"]')).to_have_count(1)
                expect(nav.locator('[data-view="organizer"]')).to_have_count(0)
                nav.locator('[data-view="'+view+'"]').click()
                expect(page.locator('#demo-app')).to_have_attribute('data-screen',view)
                expect(page.locator('.unified-navigation')).not_to_be_visible()
                expect(page.locator('.unified-navigation [aria-current="page"]')).to_have_count(1)
            page.locator('#role').select_option('organizer');page.get_by_role('button',name='Menu',exact=True).click()
            expect(page.locator('.unified-navigation [data-view="organizer"]')).to_be_visible()
            page.locator('#role').select_option('parent');page.get_by_role('button',name='Menu',exact=True).click()
            expect(page.locator('.unified-navigation [data-view="organizer"]')).to_have_count(0)
            page.goto(self.live_server_url+'/demo/events/')
            page.locator('.event-card [data-action="save"]').first.click()
            page.get_by_role('button',name='Menu',exact=True).click()
            page.locator('.unified-navigation [data-nav-key="saved"]').click()
            expect(page.locator('h1')).to_have_text('Saved')
            page.get_by_role('link',name='Saved fictional demo activities',exact=True).click()
            expect(page.locator('.event-card')).to_have_count(1)
            browser.close()
