from html.parser import HTMLParser
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import resolve
from .models import School, Membership, SavedEvent, SchoolProfile, ShortlistedSchool, Event, Collection
from django.utils import timezone
from datetime import timedelta

class SidebarParser(HTMLParser):
    def __init__(self,source):
        super().__init__();self.inside=False;self.links=[];self.feed(source)
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='aside' and attrs.get('id')=='unified-sidebar':self.inside=True
        if tag=='a' and self.inside:self.links.append(attrs)
    def handle_endtag(self,tag):
        if tag=='aside':self.inside=False

class UnifiedNavigationTests(TestCase):
    def test_all_unique_destinations_are_direct_and_resolve(self):
        for path in ['/','/discover/activities/','/schools/','/saved/','/community/','/finder/','/about/','/team/photos/','/activities/','/events/']:
            with self.subTest(path=path):
                response=self.client.get(path);self.assertEqual(response.status_code,200)
                html=response.content.decode();links=SidebarParser(html).links
                keys=[link['data-nav-key'] for link in links];hrefs=[link['href'] for link in links]
                self.assertEqual(len(keys),len(set(keys)));self.assertEqual(len(hrefs),len(set(hrefs)))
                self.assertEqual(keys[:5],['home','activities','schools','saved','family'])
                self.assertEqual(keys[-2:],['about','photos'])
                self.assertEqual(sum('aria-current' in link for link in links),1)
                self.assertNotIn('community-tools',html);self.assertNotIn('sidebar-note',html);self.assertNotIn('bottom-nav',html)
                for href in hrefs:resolve(href)
                self.assertTrue({'finder','calendar','crews','child','demo-calendar','safety','feedback','community','presentation','account'}.issubset(keys))
    def test_presentation_and_live_pages_use_same_destinations(self):
        live=self.client.get('/').context['unified_navigation']
        demo=self.client.get('/demo/').context['unified_navigation']
        self.assertEqual([(n['key'],n['url']) for n in live],[(n['key'],n['url']) for n in demo])
        for item in demo:
            if not item['url'].startswith('/demo/'):self.assertEqual(item['demo_view'],'')
        self.assertEqual([n['key'] for n in demo if n['active']],['presentation'])

    def test_legacy_event_and_activity_urls_share_one_active_item(self):
        for path in ['/events/','/activities/','/discover/activities/']:
            links=SidebarParser(self.client.get(path).content.decode()).links
            self.assertEqual([i['data-nav-key'] for i in links if 'aria-current' in i],['activities'])
    def test_staff_and_student_tools_are_preserved_with_valid_routes(self):
        school=School.objects.create(name='Navigation school',invite_code_hash='private')
        for role,expected in [('staff',{'staff','school-profile','approvals','studio','feedback-inbox','applications','moderation','announcements'}),('student',{'announcements','tickets'})]:
            user=User.objects.create_user('nav-'+role);Membership.objects.create(user=user,school=school,role=role,verified=True);self.client.force_login(user)
            links=SidebarParser(self.client.get('/').content.decode()).links;keys={i['data-nav-key'] for i in links}
            self.assertTrue(expected.issubset(keys));self.assertNotIn('organizer',keys)
            for item in links:resolve(item['href'])
    def test_saved_records_and_collections_remain_visible(self):
        user=User.objects.create_user('nav-parent');school=School.objects.create(name='Saved school',invite_code_hash='private')
        event=Event.objects.create(school=school,created_by=user,published_by=user,title='Existing saved event',description='Saved content',venue='Studio',category='Arts',start_at=timezone.now()+timedelta(days=2),status='published',visibility='public')
        SavedEvent.objects.create(user=user,event=event);Collection.objects.create(user=user,name='Existing collection')
        profile=SchoolProfile.objects.create(name='Existing shortlisted school',slug='existing-shortlist',is_published=True,source_name='Test source',last_checked=timezone.now().date());ShortlistedSchool.objects.create(user=user,profile=profile)
        self.client.force_login(user);response=self.client.get('/saved/')
        for text in ['Existing saved event','Existing collection','Existing shortlisted school','Saved activities','Shortlisted schools','Presentation saved content']:self.assertContains(response,text)
        self.assertEqual(SavedEvent.objects.filter(user=user).count(),1);self.assertEqual(ShortlistedSchool.objects.filter(user=user).count(),1)
