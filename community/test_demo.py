"""Previously shared URLs lead to the persistent application, with real authorization."""
import re
from django.test import TestCase
from django.contrib.auth.models import User
from .models import Event,Membership,ParentAccount,ChildProfile,Participation

class LegacyRouteTests(TestCase):
    def test_public_home_is_the_live_search_not_sample_content(self):
        response=self.client.get('/')
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'Discover. Connect. Belong.')
        body=re.sub(r'<script.*?</script>','',response.content.decode(),flags=re.S)
        self.assertNotRegex(body,r'(?i)demo|simulated|fictional|presentation mode')
        self.assertNotIn('/demo/',body)
        self.assertContains(response,'/accounts/login/')
    def test_old_links_preserve_search_and_lead_to_real_pages(self):
        targets={'':'/','events':'/events/','activities':'/activities/','family':'/family/','organizer':'/organizer/','creator':'/organizer/new/','saved':'/saved/','finder':'/finder/','calendar':'/calendar/','admin':'/staff/','child':'/family/','crews':'/family/','safety':'/about/','onboarding':'/family/setup/'}
        for section,target in targets.items():
            route='/demo/'+(section+'/' if section else '')
            with self.subTest(route=route):
                response=self.client.get(route+'?lang=fr&q=art')
                self.assertEqual(response.status_code,302)
                self.assertEqual(response.url,target+'?lang=fr&q=art')
                self.assertEqual(self.client.post(route,{}).status_code,405)
        self.assertRedirects(self.client.get('/demo/events/art-afternoon/'),'/events/')
        self.assertEqual(self.client.get('/demo/about/').status_code,200)
    def test_legacy_routes_cannot_grant_simulated_roles(self):
        for route in ['/demo/family/','/demo/organizer/','/demo/admin/']:
            response=self.client.get(route+'?role=admin',follow=True)
            self.assertIn('/accounts/login/',response.redirect_chain[-1][0])
            self.assertFalse(Membership.objects.exists())
    def test_browsing_creates_no_accounts_or_business_records(self):
        for route in ['/','/demo/family/','/demo/organizer/','/demo/organizer/new/']:
            self.client.get(route)
        for model in [User,Membership,Event,ParentAccount,ChildProfile,Participation]:self.assertFalse(model.objects.exists())
    def test_real_parent_and_organizer_permissions_remain_protected(self):
        for route in ['/family/','/organizer/','/organizer/new/','/staff/']:
            response=self.client.get(route)
            self.assertEqual(response.status_code,302);self.assertIn('/accounts/login/',response.url)
    def test_unknown_route_stays_not_found(self):
        self.assertEqual(self.client.get('/demo/unknown/').status_code,404)
