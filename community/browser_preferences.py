"""Questionnaire and all language options exercised against fictional isolated data."""
from pathlib import Path
from datetime import timedelta
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from django.contrib.auth.models import User
from django.utils import timezone
from playwright.sync_api import sync_playwright,expect
from .models import Event,School
from .localization import ACTIVE_LOCALES,catalog

@override_settings(STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class PreferenceBrowserTests(StaticLiveServerTestCase):
    def test_complete_back_settings_save_and_languages(self):
        user=User.objects.create_user('questionnaire-fixture',password='TestOnly!482')
        school=School.objects.create(name='Fictional onboarding school')
        Event.objects.create(school=school,created_by=user,published_by=user,title='Fictional science afternoon',description='This is an isolated test activity.',category='Science',city='Lisbon',venue='Test laboratory',attendance_mode='in_person',event_kind='workshop',price_amount=0,min_age=7,max_age=12,start_at=timezone.now()+timedelta(days=5),status='published',visibility='public')
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
            page.set_default_timeout(12000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(self.live_server_url+'/?lang=en')
            dialog=page.get_by_role('dialog');expect(dialog).to_be_visible()
            output=Path(__file__).resolve().parent.parent/'artifacts/onboarding';output.mkdir(parents=True,exist_ok=True)
            page.screenshot(path=str(output/'welcome-mobile.png'))
            next_button=page.locator('#onboarding-continue');next_button.click()
            page.get_by_role('radio',name='Parent',exact=True).check();next_button.click()
            page.get_by_role('checkbox',name='Science',exact=True).check();page.get_by_role('checkbox',name='Sports',exact=True).check()
            page.screenshot(path=str(output/'interests-mobile.png'))
            next_button.click();page.locator('#onboarding-back').click();expect(page.get_by_role('checkbox',name='Science',exact=True)).to_be_checked();next_button.click()
            page.get_by_role('checkbox',name='Workshops',exact=True).check();next_button.click()
            page.get_by_label('City or region',exact=True).fill('Lisbon');next_button.click()
            page.get_by_role('radio',name='In person',exact=True).check();next_button.click()
            page.get_by_role('radio',name='Free events',exact=True).check();next_button.click()
            expect(page.locator('#discovery-onboarding')).to_have_count(0)
            expect(page.get_by_role('heading',name='Recommended for You',exact=True)).to_be_visible()
            section=page.locator('section').filter(has=page.get_by_role('heading',name='Recommended for You',exact=True))
            expect(section.get_by_role('heading',name='Fictional science afternoon')).to_be_visible()
            section.get_by_role('button',name='Save Event',exact=True).click()
            expect(section.get_by_role('button',name='Save Event',exact=True)).to_have_attribute('aria-pressed','true')
            page.reload();expect(page.locator('#discovery-onboarding')).to_have_count(0)
            page.set_viewport_size({'width':1440,'height':1000});page.screenshot(path=str(output/'recommendations-desktop.png'),full_page=True)
            page.get_by_role('link',name='Change preferences',exact=True).click()
            page.locator('#id_city').fill('Cascais');page.locator('#id_language').select_option('pt-PT')
            page.get_by_role('button',name='Save preferences',exact=True).click()
            expect(page.get_by_role('status').filter(has_text=catalog('pt-PT')['Preferences saved.'])).to_be_visible()
            for locale in ACTIVE_LOCALES:
                page.locator('#interface-language').select_option(locale)
                expect(page.locator('html')).to_have_attribute('lang',locale)
                expect(page.get_by_role('heading',name=catalog(locale)['Discovery preferences'],exact=True)).to_be_visible()
                page.goto(self.live_server_url+'/schools/')
                expect(page.locator('html')).to_have_attribute('lang',locale)
                page.goto(self.live_server_url+'/settings/preferences/')
                expect(page.locator('#id_city')).to_have_value('Cascais')
            self.assertEqual(errors,[])
            for width in [390,768,1440]:
                page.set_viewport_size({'width':width,'height':900})
                self.assertTrue(page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
            browser.close()
    def test_skip_and_failure_feedback(self):
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            page=browser.new_page();page.goto(self.live_server_url+'/?lang=en')
            page.route('**/onboarding/complete/',lambda route:route.fulfill(status=503,body='Unavailable'))
            page.locator('#onboarding-skip').click()
            expect(page.get_by_role('alert')).to_contain_text('Preferences could not be saved.')
            expect(page.get_by_role('dialog')).not_to_be_visible()
            page.reload();expect(page.get_by_role('dialog')).to_be_visible()
            page.unroute('**/onboarding/complete/')
            page.locator('#onboarding-skip').click();expect(page.locator('#discovery-onboarding')).to_have_count(0)
            page.reload();expect(page.locator('#discovery-onboarding')).to_have_count(0)
            browser.close()
    def test_complete_questionnaire_in_every_language(self):
        questions=['What language do you prefer?','Are you a student, parent or teacher?','What are your main interests?','What type of events are you interested in?','In which city or region would you like to find events?','Do you prefer online events, in-person events or both?','Do you prefer free events or both free and paid events?']
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            for locale in ACTIVE_LOCALES:
                with self.subTest(locale=locale):
                    context=browser.new_context(viewport={'width':390,'height':844})
                    page=context.new_page();page.goto(self.live_server_url+'/?lang='+locale)
                    for index,question in enumerate(questions):
                        expect(page.locator('[data-onboarding-step]:not([hidden]) legend')).to_have_text(catalog(locale)[question])
                        expect(page.locator('#onboarding-progress')).to_have_attribute('value',str(index+1))
                        if index==1:page.locator('input[name=audience][value=parent]').check()
                        if index==2:page.locator('input[name=interests][value=Science]').check()
                        if index==3:page.locator('input[name=event_kinds][value=workshop]').check()
                        if index==4:page.locator('#onboarding-city').fill('Lisbon')
                        if index==5:page.locator('input[name=attendance][value=both]').check()
                        if index==6:page.locator('input[name=budget][value=free]').check()
                        page.locator('#onboarding-continue').click()
                    expect(page.locator('#discovery-onboarding')).to_have_count(0)
                    page.reload();expect(page.locator('#discovery-onboarding')).to_have_count(0)
                    self.assertTrue(page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
                    context.close()
            browser.close()
