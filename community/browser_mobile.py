"""Bundled mobile UI against an isolated live Django backend, never production."""
import os
import subprocess
import time
import urllib.request
from pathlib import Path
from datetime import timedelta
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from django.contrib.auth.models import User
from django.utils import timezone
from playwright.sync_api import sync_playwright,expect
from .models import School,Event,ParentAccount,ChildProfile

@override_settings(MOBILE_API_ENABLED=True,MOBILE_ALLOWED_ORIGINS=['http://127.0.0.1:5173'])
class MobileBrowser(StaticLiveServerTestCase):
    def test_mobile_parent_journey(self):
        parent=User.objects.create_user('native-test-parent',password='BrowserMobile!482',first_name='Test Parent')
        owner=ParentAccount.objects.create(user=parent)
        ChildProfile.objects.create(parent=owner,nickname='Fictional explorer',age_band='9-11',languages='en',interests='Arts')
        school=School.objects.create(name='Fictional browser school')
        event=Event.objects.create(school=school,created_by=parent,published_by=parent,title='Fictional art workshop',description='An isolated browser test, not a real activity.',category='Arts',venue='Test studio',visibility='public',status='published',min_age=7,max_age=12,languages='en',area='Lisbon',price_amount=0,start_at=timezone.now()+timedelta(days=6),end_at=timezone.now()+timedelta(days=6,hours=1))
        workspace=Path(__file__).resolve().parent.parent
        env={**os.environ,'VITE_API_BASE_URL':self.live_server_url}
        with open('/tmp/tkzone-vite-browser.log','w') as log:
            vite=subprocess.Popen(['npm','run','dev'],cwd=workspace/'mobile',env=env,stdout=log,stderr=log,start_new_session=True)
            try:
                for _ in range(60):
                    try:urllib.request.urlopen('http://127.0.0.1:5173',timeout=1);break
                    except Exception:time.sleep(.1)
                with sync_playwright() as pw:
                    browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
                    page=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
                    page.set_default_timeout(15000);errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                    page.goto('http://127.0.0.1:5173/#/')
                    expect(page.get_by_role('heading',name='Big discoveries for little explorers.')).to_be_visible()
                    output=workspace/'artifacts/mobile';output.mkdir(parents=True,exist_ok=True)
                    page.screenshot(path=str(output/'home.png'),full_page=True)
                    page.get_by_role('link',name='Sign in',exact=True).click()
                    page.get_by_label('Email or username').fill('native-test-parent');page.get_by_label('Password',exact=True).fill('BrowserMobile!482')
                    page.get_by_role('button',name='Sign in',exact=True).click();expect(page.get_by_role('heading',name='Your family')).to_be_visible()
                    page.get_by_role('link',name='Activities',exact=True).click()
                    page.get_by_label('Age',exact=True).fill('11');page.get_by_label('Area',exact=True).fill('Lisbon');page.get_by_label('Language',exact=True).select_option('en');page.get_by_label('Price',exact=True).select_option('free');page.get_by_label('Category',exact=True).select_option('Arts')
                    page.get_by_role('button',name='Apply filters').click();expect(page.get_by_role('heading',name='Fictional art workshop')).to_be_visible()
                    page.get_by_role('button',name='Save',exact=True).click();expect(page.get_by_role('button',name='Saved',exact=True)).to_be_visible()
                    page.screenshot(path=str(output/'discover.png'),full_page=True)
                    page.get_by_role('link',name='Details',exact=True).click();expect(page.get_by_role('heading',name='Fictional art workshop')).to_be_visible()
                    page.screenshot(path=str(output/'detail.png'),full_page=True)
                    page.get_by_role('button',name='Plan as a family').click();expect(page.locator('#notice')).to_contain_text('Plan saved')
                    page.get_by_role('button',name='Send for parent review').click();expect(page.get_by_role('heading',name='Your family')).to_be_visible()
                    page.get_by_label('Confirm parent password').fill('BrowserMobile!482');page.get_by_role('button',name='Approve permission').click()
                    expect(page.get_by_text('Parent permission granted · awaiting organiser',exact=True)).to_be_visible()
                    page.screenshot(path=str(output/'family.png'),full_page=True)
                    page.get_by_role('link',name='Family calendar',exact=True).click();expect(page.get_by_role('heading',name='Fictional art workshop')).to_be_visible()
                    self.assertTrue(page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
                    self.assertEqual(errors,[])
                    browser.close()
            finally:
                import signal
                os.killpg(vite.pid,signal.SIGTERM);vite.wait(timeout=10)
