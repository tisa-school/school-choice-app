from datetime import timedelta
from io import BytesIO
from PIL import Image
from django.contrib.auth.models import User
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from django.utils import timezone
from playwright.sync_api import sync_playwright,expect
from .models import School,Membership,Event,SchoolProfile,SavedEvent,ParentAccount,ChildProfile,PrivateFamilyEvent,PlatformAudit,FamilyPlan

@override_settings(STORAGES={'default':{'BACKEND':'community.storage.DatabasePrivateStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class PlatformV2BrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        self.school=School.objects.create(name='Unicorn School',invite_code_hash='private')
        self.admin=User.objects.create_user('existing-admin-name',email='admin@platform.test',password='IsolatedPlatformAdmin!729')
        Membership.objects.create(user=self.admin,school=self.school,role='staff',verified=True)
        self.event=Event.objects.create(school=self.school,created_by=self.admin,published_by=self.admin,title='Test football skills workshop',description='A football workshop used only in isolated browser tests.',category='Sports',venue='Test local pitch',area='Lisbon',min_age=8,max_age=12,languages='en,pt',price_amount=0,start_at=timezone.now()+timedelta(days=3),status='published',visibility='public',contact_public=True,contact_name='Test organiser',contact_website='https://example.test/official')
        for i in range(5):SchoolProfile.objects.create(name=f'Test international school {i}',slug=f'platform-test-{i}',city='Lisbon',school_type='international',curriculum='Test curriculum',min_age=6,max_age=16,languages='en,pt',source_name='Isolated test source',source_url='https://example.test/school',last_checked=timezone.now().date(),is_published=True)
    def launch(self,p,width=1440):
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':width,'height':1000},reduced_motion='reduce');page.set_default_timeout(10000);return browser,page
    def test_visitor_search_four_school_comparison_mobile_and_portuguese(self):
        with sync_playwright() as p:
            browser,page=self.launch(p);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(self.live_server_url+'/');expect(page.get_by_role('heading',level=1)).to_have_text('Discover more for your family in Lisbon.')
            expect(page.locator('.unified-navigation a')).to_have_count(5)
            page.screenshot(path='/tmp/tkzone-v2-home-desktop.png',full_page=True)
            page.locator('#smart-q').fill('football');page.locator('.smart-discovery button').click()
            expect(page.locator('main')).to_contain_text(self.event.title)
            page.get_by_role('heading',name=self.event.title,exact=True).get_by_role('link').click()
            page.context.route('https://example.test/official',lambda route:route.fulfill(status=200,content_type='text/html',body='<h1>Isolated official-provider test page</h1>'))
            with page.expect_popup() as popup:page.get_by_role('link',name='Organizer website',exact=False).click()
            expect(popup.value.locator('h1')).to_contain_text('Isolated official-provider')
            page.goto(self.live_server_url+'/schools/?q=Test+international')
            for i in range(4):page.locator(f'[data-compare-school="platform-test-{i}"]').check()
            page.locator('[data-compare-school="platform-test-4"]').click();expect(page.locator('[data-compare-school="platform-test-4"]')).not_to_be_checked()
            page.locator('#school-compare-bar a').click();expect(page.locator('.school-comparison thead th')).to_have_count(5)
            page.screenshot(path='/tmp/tkzone-v2-schools-comparison.png',full_page=True)
            for width in [390,768,1440]:
                page.set_viewport_size({'width':width,'height':1000});page.goto(self.live_server_url+'/?lang=pt-PT')
                expect(page.get_by_role('heading',level=1)).to_have_text('Descubra mais para a sua família em Lisboa.')
                self.assertFalse(page.evaluate('document.documentElement.scrollWidth>innerWidth'))
                if width==390:
                    page.screenshot(path='/tmp/tkzone-v2-home-mobile.png',full_page=True)
                    page.get_by_role('button',name='Menu',exact=True).click();expect(page.locator('.unified-navigation')).to_be_visible();expect(page.locator('.unified-navigation a')).to_have_count(5)
                    page.keyboard.press('Escape');expect(page.locator('.unified-navigation')).not_to_be_visible()
            self.assertEqual(errors,[]);browser.close()
    def test_parent_signup_profile_photo_calendar_and_new_login_persist(self):
        out=BytesIO();Image.new('RGB',(100,100),'purple').save(out,'PNG')
        with sync_playwright() as p:
            browser,page=self.launch(p,390)
            page.goto(self.live_server_url+'/accounts/signup/?family=1')
            page.locator('#id_name').fill('Isolated Parent');page.locator('#id_email').fill('family@isolated.test');page.locator('#id_password1').fill('UniqueFamilyBrowser!729');page.locator('#id_password2').fill('UniqueFamilyBrowser!729')
            page.get_by_role('button',name='Create account ✦',exact=True).click();page.wait_for_url('**/family/setup/')
            page.locator('#id_guardian_consent').check();page.get_by_role('button',name='Create my family workspace ✦',exact=True).click()
            page.goto(self.live_server_url+'/family/children/new/')
            page.locator('#id_nickname').fill('Fictional Child');page.locator('#id_age_band').select_option('9-11');page.locator('#id_interests').fill('Art');page.locator('#id_languages').fill('en')
            page.locator('#id_photo').set_input_files({'name':'private.png','mimeType':'image/png','buffer':out.getvalue()});page.locator('#id_photo_permission').check();page.get_by_role('button',name='Save child profile ✦',exact=True).click()
            expect(page.locator('.private-child-portrait')).to_be_visible();photo_url=page.locator('.private-child-portrait').get_attribute('src')
            page.goto(self.live_server_url+f'/events/{self.event.pk}/');page.get_by_role('button',name='♡ Save for later',exact=True).click();page.get_by_role('button',name='Add to family plan',exact=False).click()
            page.goto(self.live_server_url+'/family/private-events/new/')
            day=(timezone.now()+timedelta(days=2)).strftime('%Y-%m-%d');page.locator('#id_title').fill('Private family test plan');page.locator('#id_start_at').fill(day+'T14:00');page.locator('#id_end_at').fill(day+'T15:00');page.get_by_role('button',name='Save calendar event',exact=True).click()
            expect(page.locator('.family-calendar-grid')).to_contain_text('Private family test plan')
            page.screenshot(path='/tmp/tkzone-v2-family-calendar-mobile.png',full_page=True)
            response=page.request.get(self.live_server_url+'/family/calendar.ics');self.assertEqual(response.status,200);self.assertIn('Private family test plan',response.text())
            page.locator('.platform-account summary').click();page.get_by_role('button',name='Log Out',exact=True).click()
            self.assertEqual(page.request.get(self.live_server_url+photo_url,max_redirects=0).status,302)
            page.goto(self.live_server_url+'/accounts/login/?next=/family/')
            page.locator('#id_username').fill('family@isolated.test');page.locator('#id_password').fill('UniqueFamilyBrowser!729');page.get_by_role('button',name='Log In ✦',exact=True).click()
            expect(page.locator('.private-child-portrait')).to_be_visible();page.goto(self.live_server_url+'/saved/');expect(page.locator('main')).to_contain_text(self.event.title)
            page.goto(self.live_server_url+'/family/calendar/');expect(page.locator('.family-calendar-grid')).to_contain_text('Private family test plan');browser.close()
    def test_eight_step_tour_reset_and_production_isolation(self):
        before=(SavedEvent.objects.count(),ParentAccount.objects.count(),ChildProfile.objects.count(),PrivateFamilyEvent.objects.count(),FamilyPlan.objects.count(),PlatformAudit.objects.count())
        with sync_playwright() as p:
            browser,page=self.launch(p,390);mutations=[];page.on('request',lambda request:mutations.append(request.url) if request.method=='POST' else None)
            page.goto(self.live_server_url+'/tour/')
            for step in range(8):
                expect(page.locator('.tour-progress')).to_contain_text(f'{step+1}/8')
                if step==1:page.locator('#tour-search').fill('football');expect(page.locator('#tour-search-results')).to_contain_text(self.event.title)
                if step==2:page.locator('[data-tour-action="school"]').first.click()
                if step==3:page.locator('[data-tour-action="save"]').first.click()
                if step==4:page.locator('#tour-plan-day').fill('2026-11-20');page.locator('[data-tour-action="plan"]').click()
                if step==5:page.locator('[data-tour-action="interest"]').first.click()
                if step==6:page.locator('[data-tour-action="report"]').click()
                self.assertFalse(page.evaluate('document.documentElement.scrollWidth>innerWidth'))
                if step<7:page.locator('[data-tour-action="next"]').click()
            page.screenshot(path='/tmp/tkzone-v2-tour-complete.png',full_page=True)
            expect(page.locator('#product-tour')).to_contain_text('No booking, message, publication or payment has been made.')
            page.locator('[data-tour-action="back"]').click();expect(page.locator('.tour-progress')).to_contain_text('7/8')
            page.locator('[data-tour-action="restart"]').click();expect(page.locator('.tour-progress')).to_contain_text('1/8')
            page.reload();expect(page.locator('.tour-progress')).to_contain_text('1/8');self.assertEqual(mutations,[])
            self.assertEqual(page.request.get(self.live_server_url+'/manage/tour/').status,403);browser.close()
        self.assertEqual(before,(SavedEvent.objects.count(),ParentAccount.objects.count(),ChildProfile.objects.count(),PrivateFamilyEvent.objects.count(),FamilyPlan.objects.count(),PlatformAudit.objects.count()))
