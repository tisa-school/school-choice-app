import importlib
import json
from types import SimpleNamespace
from django.apps import apps
from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from . import test_organizers as fixtures
from .demo_access import access_for
from .models import TeamPhoto, School, Membership


class BrandRoleTests(TestCase):
    @classmethod
    def setUpTestData(cls):fixtures.OrganizerStudioTests.setUpTestData.__func__(cls)

    def test_parents_children_and_unverified_organisers_cannot_open_or_post_studio(self):
        self.another_member.verified=False;self.another_member.save()
        for user in [self.parent,self.student,self.another]:
            self.client.force_login(user)
            for path in ['/organizer/','/organizer/new/','/demo/organizer/','/demo/creator/','/demo/organizer/new/']:
                with self.subTest(user=user.pk,path=path):
                    self.assertEqual(self.client.get(path+'?role=organizer').status_code,403)
            self.assertEqual(self.client.post('/organizer/new/',{'role':'organizer','title':'Forbidden draft'}).status_code,403)
            for path in ['/organizer/ai-draft/','/demo/ai-draft/','/demo/moderation-check/']:
                self.assertEqual(self.client.post(path,json.dumps({'role':'organizer'}),content_type='application/json').status_code,403)
            body=self.client.get('/community/').content.decode().split('<script id="ui-catalog"')[0]
            self.assertNotIn('Organiser studio',body)
            self.assertNotIn('Organizer demo',body)
            self.assertNotIn('Try posting an event',body)

    def test_verified_organiser_gets_studio_and_account_bound_role(self):
        self.client.force_login(self.organizer)
        self.assertContains(self.client.get('/community/'),'Organiser studio')
        self.assertEqual(self.client.get('/organizer/').status_code,200)
        self.assertEqual(self.client.get('/demo/organizer/').status_code,200)
        self.assertEqual(access_for(self.organizer)['roles'],['organizer'])
        self.assertEqual(self.client.get('/demo/admin/').status_code,403)

    def test_guest_presentation_roles_are_explicitly_fictional(self):
        self.assertEqual(self.client.get('/demo/organizer/').status_code,200)
        self.assertEqual(access_for(self.client.request().wsgi_request.user)['roles'],['child','parent','organizer','admin'])
        for user,role in [(self.parent,'parent'),(self.student,'child'),(self.staff,'admin')]:
            self.assertEqual(access_for(user)['roles'],[role])
            self.client.force_login(user)
            self.assertEqual(self.client.get('/demo/about/').status_code,200)
            self.client.logout()

    def test_name_and_legacy_portrait_displays_are_correct(self):
        from .team import canonical_team_text
        self.assertEqual(canonical_team_text('Portrait: Sophia Gateneo'),'Portrait: Sophia Gatenyo')
        for path in ['/about/','/demo/about/']:
            response=self.client.get(path)
            self.assertContains(response,'Sophia Gatenyo')
            self.assertNotContains(response,'Sophia Gateneo')

    def test_name_migration_preserves_image_ids_permissions_and_other_schools(self):
        migration=importlib.import_module('community.migrations.0011_correct_sophia_name')
        school=School.objects.create(name='Unicorn School',invite_code_hash='unchanged')
        photo=TeamPhoto.objects.create(school=school,uploaded_by=self.staff,name='Sophia Gateneo',caption='Sophia Gateneo · team',description='Portrait of Sophia Gateneo',image='team/unchanged.jpg',visibility='private',sharing_permission=False,guardian_consent=False)
        other=TeamPhoto.objects.create(school=School.objects.create(name='Other school'),uploaded_by=self.staff,name='Sophia Gateneo',description='Unrelated',image='team/other.jpg')
        user=User.objects.create_user('unchanged-login',first_name='Sophia',last_name='Gateneo')
        Membership.objects.create(user=user,school=school,role='student')
        for _ in range(2):migration.correct_name(apps,SimpleNamespace(connection=connection))
        photo.refresh_from_db();other.refresh_from_db();user.refresh_from_db()
        self.assertEqual(photo.name,'Sophia Gatenyo');self.assertEqual(photo.caption,'Sophia Gatenyo · team')
        self.assertEqual(photo.description,'Portrait of Sophia Gatenyo')
        self.assertEqual(photo.image.name,'team/unchanged.jpg');self.assertEqual(photo.visibility,'private')
        self.assertFalse(photo.sharing_permission or photo.guardian_consent)
        self.assertEqual(other.name,'Sophia Gateneo');self.assertEqual(user.last_name,'Gatenyo');self.assertEqual(user.username,'unchanged-login')
