from datetime import timedelta
from pathlib import Path
import tempfile
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from django.utils import timezone
from playwright.sync_api import sync_playwright, expect
from .models import School, Membership, Event
from .browser_tests import db_read

@override_settings(STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}},MEDIA_ROOT=tempfile.gettempdir()+'/tkzone-image-review-tests')
class ImageReviewBrowserTests(StaticLiveServerTestCase):
    def test_organiser_reviews_crop_alt_source_and_detail_edits_reset_confirmation(self):
        school=School.objects.create(name='Image review test school')
        user=User.objects.create_user('review-organiser@test.invalid')
        Membership.objects.create(user=user,school=school,role='organizer',verified=True)
        event=Event.objects.create(school=school,created_by=user,title='Watercolour drawing',category='Arts',description='Draw Lisbon together with watercolours.',venue='Alfama arts studio',area='Alfama',activity_environment='indoor',min_age=8,max_age=16,start_at=timezone.now()+timedelta(days=5),end_at=timezone.now()+timedelta(days=5,hours=2),status='draft')
        self.client.force_login(user)
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            context=browser.new_context(viewport={'width':1440,'height':1000})
            context.add_cookies([{'name':settings.SESSION_COOKIE_NAME,'value':self.client.cookies[settings.SESSION_COOKIE_NAME].value,'url':self.live_server_url}])
            page=context.new_page();page.goto(self.live_server_url+f'/organizer/{event.pk}/')
            image=settings.BASE_DIR/'static/community/imagery/activity-drawing-768.webp'
            page.locator('#id_image').set_input_files(str(image))
            alt='Children drawing with watercolours at a shared indoor arts studio table.'
            page.locator('#id_image_alt').fill(alt)
            page.locator('#id_image_source').select_option('generated')
            for _ in range(3):page.get_by_role('button',name='Continue →',exact=True).click()
            expect(page.locator('#image-review-preview')).to_be_visible()
            expect(page.locator('#image-review-preview')).to_have_attribute('alt',alt)
            page.locator('#id_image_reviewed').check()
            page.get_by_role('button',name='← Previous',exact=True).click()
            page.locator('#id_min_age').fill('9')
            expect(page.locator('#id_image_reviewed')).not_to_be_checked()
            page.get_by_role('button',name='Continue →',exact=True).click()
            page.locator('#id_image_reviewed').check()
            page.get_by_role('button',name='Save draft',exact=True).click()
            page.wait_for_url('**/organizer/')
            self.assertTrue(db_read(lambda:Event.objects.get(pk=event.pk).image_is_reviewed))
            page.goto(self.live_server_url+f'/organizer/events/{event.pk}/?preview=1')
            expect(page.locator('.detail-image img')).to_have_attribute('alt',alt)
            expect(page.locator('.detail-image')).to_contain_text('AI illustration · not this event')
            page.screenshot(path='/tmp/tkzone-image-review.png')
            browser.close()
