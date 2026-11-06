"""The approved grant is one-time, school-scoped, and leaves authentication intact."""
import importlib
from types import SimpleNamespace
from unittest.mock import patch
from django.apps import apps
from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from .models import School, Membership

grant = importlib.import_module('community.migrations.0008_grant_requested_photo_administrator')


class PhotoAdministratorGrantTests(TestCase):
    def account(self, **extra):
        user = User.objects.create_user(grant.TARGET_EMAIL, email=grant.TARGET_EMAIL, password='OnlyForIsolatedTests!729', **extra)
        return user
    def run_grant(self, environment='production'):
        with patch.dict('os.environ', {'VERCEL_ENV':environment}):
            grant.grant_requested_access(apps, SimpleNamespace(connection=connection))
    def test_existing_account_gets_photo_access_without_global_superuser_or_password_change(self):
        user=self.account();original_password=user.password
        self.run_grant()
        user.refresh_from_db();member=Membership.objects.get(user=user)
        self.assertEqual(member.school.name,'Unicorn School');self.assertEqual(member.role,'staff');self.assertTrue(member.verified)
        self.assertEqual(user.password,original_password);self.assertFalse(user.is_superuser);self.assertFalse(user.is_staff)
        self.client.force_login(user);self.assertEqual(self.client.get('/team/photos/new/').status_code,200)
        self.assertEqual(self.client.get('/staff/content/').status_code,200)
    def test_missing_account_fails_without_creating_account_or_school(self):
        with self.assertRaises(RuntimeError):self.run_grant()
        self.assertFalse(User.objects.exists());self.assertFalse(School.objects.exists());self.assertFalse(Membership.objects.exists())
    def test_inactive_account_is_not_activated_or_granted_access(self):
        user=self.account(is_active=False)
        with self.assertRaises(RuntimeError):self.run_grant()
        user.refresh_from_db();self.assertFalse(user.is_active);self.assertFalse(Membership.objects.exists())
    def test_unusable_password_is_not_replaced(self):
        user=self.account();user.set_unusable_password();user.save();original=user.password
        with self.assertRaises(RuntimeError):self.run_grant()
        user.refresh_from_db();self.assertEqual(user.password,original);self.assertFalse(Membership.objects.exists())
    def test_duplicate_emails_fail_closed(self):
        self.account();User.objects.create_user('duplicate-test',email=grant.TARGET_EMAIL,password='OtherIsolatedTest!729')
        with self.assertRaises(RuntimeError):self.run_grant()
        self.assertFalse(Membership.objects.exists())
    def test_existing_other_school_membership_is_not_overwritten(self):
        user=self.account();school=School.objects.create(name='Another school',invite_code_hash='test-only')
        member=Membership.objects.create(user=user,school=school,role='parent')
        with self.assertRaises(RuntimeError):self.run_grant()
        member.refresh_from_db();self.assertEqual(member.school_id,school.pk);self.assertEqual(member.role,'parent');self.assertFalse(member.verified)
    def test_idempotent_and_does_not_create_working_school_invitation(self):
        user=self.account();self.run_grant();self.run_grant()
        self.assertEqual(School.objects.count(),1);self.assertEqual(Membership.objects.count(),1)
        self.assertFalse(Membership.objects.get(user=user).school.valid_invite('any-public-code'))
    def test_preview_and_local_runs_cannot_grant_access(self):
        user=self.account()
        for environment in ['preview','development','']:
            self.run_grant(environment)
            self.assertFalse(Membership.objects.filter(user=user).exists())
