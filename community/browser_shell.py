"""Shared chrome and responsive regressions for demo and live Django pages."""
from pathlib import Path
from django.conf import settings
from django.test import override_settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from playwright.sync_api import sync_playwright,expect

@override_settings(STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class ProductShellBrowserTests(StaticLiveServerTestCase):
    def test_shared_header_sidebar_typography_and_mobile_navigation(self):
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':1440,'height':1000});errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.emulate_media(reduced_motion='reduce')
            for locale in ['en','pt-PT','ar']:
                for width in [360,390,768,1024,1440]:
                    page.set_viewport_size({'width':width,'height':1000})
                    reference=None
                    for route in ['/demo/','/community/','/finder/']:
                        response=page.goto(self.live_server_url+route+'?lang='+locale)
                        self.assertEqual(response.status,200)
                        if width<=800:page.locator('.nav-menu-toggle').click()
                        page.locator('.product-sidebar').wait_for()
                        if page.evaluate('document.documentElement.scrollWidth > innerWidth'):
                            page.screenshot(path='/tmp/product-shell-overflow.png',full_page=True)
                            print(page.evaluate("[...document.querySelectorAll('.product-header,.top-actions,.language-picker,.header-join,.product-sidebar,main,.community-invite,.hero,footer')].map(e=>({tag:e.className,width:e.clientWidth,scroll:e.scrollWidth,rect:e.getBoundingClientRect().toJSON()}))"))
                        self.assertFalse(page.evaluate('document.documentElement.scrollWidth > innerWidth'),f'{locale} {width} {route}: '+str(page.evaluate("[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1).slice(0,5).map(e=>e.tagName+'.'+e.className)")))
                        styles=page.evaluate("""()=>{const style=s=>getComputedStyle(document.querySelector(s));return {brand:style('.product-brand').color,header:style('.product-header').backgroundColor,sidebar:style('.product-sidebar').width,font:style('body').fontFamily,background:style('body').backgroundColor};}""")
                        if reference:self.assertEqual(styles,reference,f'Chrome mismatch: {width} {route}')
                        else:reference=styles
                        self.assertTrue(page.locator('.product-header').is_visible())
                        self.assertTrue(page.locator('.product-sidebar').is_visible())
            page.goto(self.live_server_url+'/community/?lang=en')
            expect(page.locator('.product-sidebar a[href="/community/"]')).to_have_attribute('aria-current','page')
            page.goto(self.live_server_url+'/finder/')
            expect(page.get_by_label('Search preferences only',exact=True)).to_be_visible()
            expect(page.locator('.product-sidebar a[href="/discover/activities/"]')).to_have_attribute('aria-current','page')
            self.assertTrue(page.locator('input[name="csrfmiddlewaretoken"]').count())
            page.set_viewport_size({'width':1440,'height':1000})
            folder=Path(settings.BASE_DIR)/'docs/screenshots'
            page.screenshot(path=str(folder/'unified-finder.png'),full_page=True)
            page.goto(self.live_server_url+'/community/?lang=en')
            page.screenshot(path=str(folder/'unified-community.png'),full_page=True)
            page.set_viewport_size({'width':390,'height':844})
            page.screenshot(path=str(folder/'unified-community-mobile.png'),full_page=True)
            page.keyboard.press('Tab')
            self.assertTrue(page.evaluate('document.activeElement!==document.body'))
            self.assertEqual(errors,[]);browser.close()
