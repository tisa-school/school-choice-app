from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import Event,School,Membership,ParentAccount,ChildProfile,Participation,SaveReceipt
from django.utils import timezone

class PresentationModeTests(TestCase):
    def test_home_opens_presentation_without_registration(self):
        response=self.client.get('/')
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'Presentation mode')
        self.assertContains(response,'No registration')
        self.assertNotContains(response,'type="password"')
        self.assertNotContains(response,'type="email"')
    def test_all_demo_pages_available_without_login(self):
        for route in ['/demo/','/demo/events/','/demo/activities/','/demo/family/','/demo/organizer/','/demo/organizer/new/','/demo/saved/','/demo/finder/','/demo/events/art-afternoon/']:
            with self.subTest(route=route):
                response=self.client.get(route)
                self.assertEqual(response.status_code,200)
                self.assertContains(response,'fictional sample content')
                self.assertEqual(response['Cache-Control'],'no-store')
    def test_visiting_demo_creates_no_accounts_or_business_records(self):
        models=[User,Membership,Event,ParentAccount,ChildProfile,Participation,SaveReceipt]
        before=[model.objects.count() for model in models]
        for route in ['/','/demo/family/','/demo/organizer/','/demo/organizer/new/']: self.client.get(route)
        self.assertEqual(before,[model.objects.count() for model in models])
    def test_demo_post_cannot_modify_real_data(self):
        response=self.client.post('/demo/organizer/new/',{'title':'Not a real listing','role':'staff'})
        self.assertEqual(response.status_code,405)
        self.assertFalse(Event.objects.filter(title='Not a real listing').exists())
        self.assertFalse(User.objects.exists())
    def test_real_parent_and_organizer_permissions_remain_protected(self):
        for route in ['/family/','/organizer/','/organizer/new/','/staff/']:
            response=self.client.get(route)
            self.assertEqual(response.status_code,302)
            self.assertIn('/accounts/login/',response.url)
    def test_authenticated_visitors_do_not_leak_private_profile_into_demo(self):
        user=User.objects.create_user('private-user',first_name='Private real name')
        parent=ParentAccount.objects.create(user=user)
        ChildProfile.objects.create(parent=parent,nickname='Private real child',age_band='9-11')
        self.client.force_login(user)
        response=self.client.get('/demo/family/')
        self.assertNotContains(response,'Private real name')
        self.assertNotContains(response,'Private real child')
    def test_live_community_remains_publicly_accessible(self):
        response=self.client.get('/community/')
        self.assertEqual(response.status_code,200)
        self.assertNotContains(response,'id="demo-catalog"')
    def test_nonexistent_demo_routes_return_404(self):
        self.assertEqual(self.client.get('/demo/unknown/').status_code,404)

    def test_final_demo_routes_and_network_boundaries(self):
        for section in ['child','crews','admin','safety','about','onboarding','creator']:
            response=self.client.get('/demo/'+section+'/')
            self.assertEqual(response.status_code,200)
            self.assertIn("connect-src 'self'",response['Content-Security-Policy'])
            self.assertIn("form-action 'none'",response['Content-Security-Policy'])
            self.assertEqual(self.client.post('/demo/'+section+'/',{}).status_code,405)
