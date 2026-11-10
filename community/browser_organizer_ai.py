import json
from django.test import override_settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from playwright.sync_api import sync_playwright,expect
from .browser_tests import db_read
from .models import Event

DRAFT={'title':{'en':'Creative Art Workshop','pt':'Oficina de arte criativa'},'description':{'en':'Explore drawing together.','pt':'Explora o desenho em conjunto.'},'min_age':8,'max_age':12,'category':'Arts','languages':['en'],'accessibility':{'en':'Step-free access.','pt':'Acesso sem degraus.'}}
@override_settings(STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class OrganizerAIBrowserTests(StaticLiveServerTestCase):
    def test_review_apply_edit_and_submission_remain_separate(self):
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':390,'height':844});page.goto(self.live_server_url+'/demo/creator/')
            calls=[]
            def reply(route):
                calls.append(route.request.post_data_json)
                route.fulfill(status=200,content_type='application/json',body=json.dumps({'source':'ai','draft':DRAFT}))
            page.route('**/demo/ai-draft/',reply)
            page.locator('[data-ai-brief]').fill('An English art workshop for ages 8–12 with step-free access.')
            original_day=page.locator('#field-day').input_value();original_price=page.locator('#field-price').input_value()
            page.get_by_role('button',name='Fill with AI ✦',exact=True).click()
            expect(page.get_by_role('dialog')).to_contain_text('Creative Art Workshop')
            expect(page.locator('#field-title')).to_have_value('')
            from pathlib import Path
            from django.conf import settings
            page.get_by_role('dialog').screenshot(path=str(Path(settings.BASE_DIR)/'docs/screenshots/organizer-ai-review.png'))
            page.get_by_role('button',name='Use draft fields',exact=True).click()
            expect(page.locator('#field-title')).to_have_value('Creative Art Workshop')
            expect(page.locator('#field-titlePt')).to_have_value('Oficina de arte criativa')
            expect(page.locator('#field-minAge')).to_have_value('8');expect(page.locator('#field-maxAge')).to_have_value('12')
            expect(page.locator('#field-languages')).to_have_value('English')
            expect(page.locator('#accessibility-en')).to_have_value('Step-free access.')
            expect(page.locator('#field-day')).to_have_value(original_day);expect(page.locator('#field-price')).to_have_value(original_price)
            self.assertFalse(db_read(lambda:Event.objects.exists()))
            page.locator('#field-title').fill('Our edited art workshop')
            page.locator('#field-area').fill('Alfama')
            page.get_by_role('button',name='Preview activity',exact=True).click()
            page.get_by_role('dialog').get_by_role('button',name='Submit for review',exact=True).click()
            expect(page.locator('.request-row',has_text='Our edited art workshop')).to_contain_text('Awaiting simulated review')
            self.assertEqual(calls,[{'brief':'An English art workshop for ages 8–12 with step-free access.'}]);self.assertFalse(page.evaluate('document.documentElement.scrollWidth>innerWidth'))
            browser.close()
    def test_unavailable_provider_preserves_existing_edits(self):
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            page=browser.new_page();page.goto(self.live_server_url+'/demo/creator/')
            page.locator('#field-title').fill('Keep my work');page.locator('[data-ai-brief]').fill('An art workshop')
            page.route('**/demo/ai-draft/',lambda route:route.fulfill(status=503,content_type='application/json',body='{}'))
            page.get_by_role('button',name='Fill with AI ✦',exact=True).click()
            expect(page.locator('[data-ai-status]')).to_contain_text('unavailable')
            expect(page.locator('#field-title')).to_have_value('Keep my work')
            browser.close()
    def test_live_editor_mapping_and_draft_only_save(self):
        from django.contrib.auth.models import User
        from .models import School,Membership
        school=School.objects.create(name='Isolated AI organiser school',invite_code_hash='test-only-placeholder')
        user=User.objects.create_user('ai-editor@test.invalid',email='ai-editor@test.invalid',password='EditorTestOnly!482')
        Membership.objects.create(user=user,school=school,role='organizer',verified=True)
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            page=browser.new_page();page.goto(self.live_server_url+'/accounts/login/')
            page.locator('#id_username').fill('ai-editor@test.invalid');page.locator('#id_password').fill('EditorTestOnly!482')
            page.get_by_role('button',name='Log In ✦',exact=True).click();page.wait_for_url('**/')
            page.goto(self.live_server_url+'/organizer/new/')
            page.route('**/organizer/ai-draft/',lambda route:route.fulfill(status=200,content_type='application/json',body=json.dumps({'source':'ai','draft':DRAFT})))
            page.locator('[data-ai-brief]').fill('An English art workshop for ages 8–12 with step-free access.')
            price=page.locator('#id_price_amount').input_value()
            page.get_by_role('button',name='Fill with AI ✦',exact=True).click()
            page.get_by_role('button',name='Use draft fields',exact=True).click()
            expect(page.locator('#id_title')).to_have_value('Creative Art Workshop')
            expect(page.locator('#id_languages')).to_have_value('en')
            expect(page.locator('#id_accessibility')).to_have_value('Step-free access.')
            expect(page.locator('#id_price_amount')).to_have_value(price)
            self.assertEqual(db_read(lambda:Event.objects.count()),0)
            page.locator('#id_start_at').fill('2026-11-21T14:00')
            page.get_by_role('button',name='Save draft',exact=True).click();page.wait_for_url('**/organizer/')
            self.assertEqual(db_read(lambda:Event.objects.get(title='Creative Art Workshop').status),'draft')
            browser.close()
