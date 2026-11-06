import importlib
from types import SimpleNamespace
from unittest.mock import patch
from django.apps import apps
from django.db import connection
from django.test import TestCase,override_settings
from . import test_about_refresh
from .models import TeamPhoto,School
import tempfile

publication=importlib.import_module('community.migrations.0009_publish_approved_about_portraits')

@override_settings(MEDIA_ROOT=tempfile.gettempdir()+'/tkzone-publication-tests')
class PortraitPublicationTests(TestCase):
    setUpTestData=classmethod(test_about_refresh.AboutRefreshTests.setUpTestData.__func__)
    portrait=test_about_refresh.AboutRefreshTests.portrait
    def publish(self,environment='production'):
        with patch.dict('os.environ',{'VERCEL_ENV':environment}):
            publication.publish_approved_portraits(apps,SimpleNamespace(connection=connection))
    def test_publication_exposes_latest_approved_portraits_to_anonymous_visitors(self):
        old=self.portrait();latest=self.portrait()
        student=self.portrait(name='Sophia Gateneo',is_student=True)
        self.publish();self.publish()
        old.refresh_from_db();self.assertEqual(old.visibility,'private')
        for photo in [latest,student]:
            photo.refresh_from_db();self.assertEqual(photo.visibility,'public')
            self.assertTrue(photo.sharing_permission);self.assertTrue(photo.guardian_consent)
            url=f'/protected-photos/team/{photo.pk}/'
            self.assertEqual(self.client.get(url).status_code,200)
            self.assertContains(self.client.get('/about/'),url)
            self.assertContains(self.client.get('/demo/about/'),url)
    def test_other_schools_groups_and_people_remain_private(self):
        self.portrait()
        other_school=School.objects.create(name='Other school',invite_code_hash='test')
        unrelated=[self.portrait(school=other_school),self.portrait(name='Someone else'),self.portrait(is_group=True)]
        self.publish()
        for photo in unrelated:
            photo.refresh_from_db();self.assertEqual(photo.visibility,'private')
            self.assertEqual(self.client.get(f'/protected-photos/team/{photo.pk}/').status_code,404)
    def test_nonproduction_runs_do_not_publish(self):
        photo=self.portrait()
        for environment in ['preview','development','']:
            self.publish(environment);photo.refresh_from_db();self.assertEqual(photo.visibility,'private')
    def test_empty_or_ambiguous_scope_fails_safely(self):
        with self.assertRaises(RuntimeError):self.publish()
        self.portrait();School.objects.create(name='Unicorn School',invite_code_hash='test')
        with self.assertRaises(RuntimeError):self.publish()
        self.assertFalse(TeamPhoto.objects.filter(visibility='public').exists())

    def test_new_student_publication_only_changes_latest_three_students(self):
        update=importlib.import_module('community.migrations.0010_publish_updated_student_portraits')
        lead=self.portrait()
        older=self.portrait(name='Sophia Gateneo',is_student=True)
        students=[self.portrait(name=name,is_student=True) for name in update.NAMES]
        with patch.dict('os.environ',{'VERCEL_ENV':'production'}):
            update.publish_updated_student_portraits(apps,SimpleNamespace(connection=connection))
            update.publish_updated_student_portraits(apps,SimpleNamespace(connection=connection))
        for photo in students:
            photo.refresh_from_db();self.assertEqual(photo.visibility,'public')
            self.assertTrue(photo.sharing_permission and photo.guardian_consent)
            url=f'/protected-photos/team/{photo.pk}/'
            self.assertEqual(self.client.get(url).status_code,200)
            self.assertContains(self.client.get('/about/'),url)
        for photo in [lead,older]:
            photo.refresh_from_db();self.assertEqual(photo.visibility,'private')
    def test_updated_student_publication_requires_all_three_and_skips_preview(self):
        update=importlib.import_module('community.migrations.0010_publish_updated_student_portraits')
        photo=self.portrait(name='Sophia Gateneo',is_student=True)
        with patch.dict('os.environ',{'VERCEL_ENV':'preview'}):
            update.publish_updated_student_portraits(apps,SimpleNamespace(connection=connection))
        with patch.dict('os.environ',{'VERCEL_ENV':'production'}):
            with self.assertRaises(RuntimeError):update.publish_updated_student_portraits(apps,SimpleNamespace(connection=connection))
        photo.refresh_from_db();self.assertEqual(photo.visibility,'private')
