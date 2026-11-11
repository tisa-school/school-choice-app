from datetime import timedelta
from django.contrib.auth.models import User
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from django.utils import timezone
from playwright.sync_api import sync_playwright, expect
from .models import School, Event, SchoolProfile

@override_settings(STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class FamilyDiscoveryBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        staff=User.objects.create_user('browser-directory-staff')
        school=School.objects.create(name='Isolated browser school',invite_code_hash='not-public')
        self.date=timezone.now()+timedelta(days=10)
        self.event=Event.objects.create(school=school,created_by=staff,published_by=staff,visibility='public',status='published',title='Garden painting',description='Outdoor watercolour painting workshop for children.',category='Arts',venue='Garden studio',area='Estrela',start_at=self.date,end_at=self.date+timedelta(hours=2),min_age=9,max_age=12,languages='en',price_amount=0,activity_environment='outdoor')
        for i in range(4):SchoolProfile.objects.create(name=f'Test school {i}',slug=f'browser-school-{i}',source_name='Browser test source',last_checked=timezone.now().date(),is_published=True,school_type='private',languages='en',stages='primary',min_age=6,max_age=12)
    def test_mobile_activity_filters_guest_saves_and_return(self):
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':390,'height':844},reduced_motion='reduce')
            page.goto(self.live_server_url+'/')
            for label in ['Explore activities','Find schools']:
                box=page.get_by_role('link',name=label,exact=False).first.bounding_box();self.assertLess(box['y']+box['height'],844)
            page.locator('.family-hero-image img').evaluate('async image=>await image.decode()')
            self.assertFalse(page.evaluate('document.documentElement.scrollWidth>innerWidth'))
            page.screenshot(path='/tmp/tkzone-family-home-mobile.png',full_page=True)
            page.get_by_role('link',name='Explore activities',exact=False).first.click()
            page.get_by_label('Search activities',exact=True).fill('painting')
            page.get_by_label('Age group',exact=True).select_option('9-12')
            page.get_by_label('From date',exact=True).fill(self.date.date().isoformat())
            page.get_by_label('To date',exact=True).fill(self.date.date().isoformat())
            page.get_by_label('Neighbourhood',exact=True).fill('Estrela')
            page.get_by_label('Price',exact=True).select_option('free')
            page.get_by_label('Setting',exact=True).select_option('outdoor')
            page.get_by_label('Activity language',exact=True).select_option('en')
            page.get_by_label('Category',exact=True).select_option('Arts')
            page.get_by_role('button',name='Apply filters',exact=True).click()
            expect(page.locator('#activity-result-count')).to_have_text('1')
            back=page.url
            page.locator('[data-save-activity]').click();expect(page.locator('[data-save-activity]')).to_have_attribute('aria-pressed','true')
            page.locator('#activity-results h3 a').click()
            expect(page.locator('h1')).to_contain_text('Garden painting')
            page.get_by_role('link',name='Back to discovery',exact=False).click()
            self.assertEqual(page.url,back)
            page.reload();expect(page.locator('[data-save-activity]')).to_have_attribute('aria-pressed','true')
            page.goto(self.live_server_url+'/saved/')
            expect(page.get_by_role('heading',name='Garden painting',exact=True)).to_be_visible()
            page.set_viewport_size({'width':1440,'height':1000});page.goto(self.live_server_url+'/');page.screenshot(path='/tmp/tkzone-family-home-desktop.png',full_page=True)
            browser.close()
    def test_school_shortlist_compare_limit_persistence_and_missing_facts(self):
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce')
            page.goto(self.live_server_url+'/schools/?q=Test+school')
            expect(page.locator('[data-school-card]')).to_have_count(4)
            page.locator('[data-save-school="browser-school-0"]').click()
            expect(page.locator('[data-save-school="browser-school-0"]')).to_have_attribute('aria-pressed','true')
            for i in range(3):page.locator(f'[data-compare-school="browser-school-{i}"]').check()
            page.locator('[data-compare-school="browser-school-3"]').click()
            expect(page.locator('[data-compare-school="browser-school-3"]')).not_to_be_checked()
            expect(page.get_by_role('status').filter(has_text='Compare up to three')).to_be_visible()
            page.locator('#school-compare-bar').get_by_role('link',name='Compare schools',exact=True).click()
            expect(page.locator('.school-comparison')).to_contain_text('Test school 0')
            expect(page.locator('.school-comparison')).to_contain_text('Not provided')
            page.screenshot(path='/tmp/tkzone-school-compare-desktop.png',full_page=True)
            page.set_viewport_size({'width':390,'height':844})
            page.wait_for_function('document.documentElement.scrollWidth<=innerWidth')
            self.assertFalse(page.evaluate('document.documentElement.scrollWidth>innerWidth'))
            page.reload();expect(page.locator('#school-compare-bar')).to_contain_text('3/3')
            page.goto(self.live_server_url+'/saved/')
            expect(page.locator('[data-school-card="browser-school-0"]')).to_be_visible()
            page.get_by_role('link',name='School profile',exact=False).click()
            expect(page.locator('h1')).to_have_text('Test school 0')
            expect(page.locator('main')).to_contain_text('Not provided')
            browser.close()
