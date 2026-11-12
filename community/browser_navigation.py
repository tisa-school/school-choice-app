from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from playwright.sync_api import sync_playwright,expect

@override_settings(STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class UnifiedSidebarBrowserTests(StaticLiveServerTestCase):
    def test_desktop_mobile_five_sections_match_and_work(self):
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce');errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            for route in ['/','/schools/','/saved/','/community/','/finder/','/about/','/team/photos/','/events/','/activities/']:
                page.goto(self.live_server_url+route);nav=page.locator('.unified-navigation')
                links=nav.locator('a').evaluate_all('items=>items.map(a=>({key:a.dataset.navKey,href:a.getAttribute("href")}))')
                self.assertEqual([i['key'] for i in links],['discover','activities','schools','family','community']);expect(nav.locator('[aria-current="page"]')).to_have_count(1)
                self.assertEqual(len(links),len({i['href'] for i in links}));expect(page.locator('.community-tools,.sidebar-note,.bottom-nav')).to_have_count(0)
                for link in links:self.assertLess(page.request.get(self.live_server_url+link['href']).status,400)
                page.set_viewport_size({'width':390,'height':844});expect(nav).not_to_be_visible()
                button=page.get_by_role('button',name='Menu',exact=True);button.click();expect(nav).to_be_visible();expect(button).to_have_attribute('aria-expanded','true')
                self.assertEqual(links,nav.locator('a').evaluate_all('items=>items.map(a=>({key:a.dataset.navKey,href:a.getAttribute("href")}))'))
                page.keyboard.press('Escape');expect(nav).not_to_be_visible();expect(button).to_be_focused();self.assertFalse(page.evaluate('document.documentElement.scrollWidth>innerWidth'))
                page.set_viewport_size({'width':1440,'height':1000})
            self.assertEqual(errors,[]);browser.close()
    def test_tour_is_reached_from_help_not_primary_navigation(self):
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':390,'height':844})
            page.goto(self.live_server_url+'/');expect(page.locator('.unified-navigation a')).to_have_count(5)
            page.locator('.platform-account summary').click();page.locator('.platform-account a[href="/help/"]').click()
            page.get_by_role('link',name='Start product tour',exact=True).click();expect(page.locator('.tour-progress')).to_contain_text('1/8')
            browser.close()
