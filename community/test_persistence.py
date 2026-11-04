from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.db import transaction
from .models import SaveReceipt, Collection
from .persistence import saved_success

class SavedDataStatusTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user('save-owner',password='SaveTesting!824')
        self.other=User.objects.create_user('other-owner',password='SaveTesting!824')
        self.client.force_login(self.user)
    def test_initial_status_does_not_claim_data_has_been_saved(self):
        self.assertContains(self.client.get('/saved/'),'No saves confirmed yet')
        self.assertFalse(SaveReceipt.objects.filter(user=self.user).exists())
    def test_successful_write_is_confirmed_with_persisted_timestamp(self):
        self.client.post('/collections/new/',{'name':'Weekend ideas','cover_style':'crystal'})
        self.assertTrue(Collection.objects.filter(user=self.user,name='Weekend ideas').exists())
        receipt=SaveReceipt.objects.get(user=self.user)
        self.assertIsNotNone(receipt.saved_at)
        self.assertContains(self.client.get('/saved/'),'Saved to database')
        self.assertContains(self.client.get('/saved/'),'Collection saved')
    def test_invalid_form_does_not_record_success(self):
        self.client.post('/collections/new/',{'name':'','cover_style':'crystal'})
        self.assertFalse(Collection.objects.filter(user=self.user).exists())
        self.assertFalse(SaveReceipt.objects.filter(user=self.user).exists())
    def test_receipt_is_private_to_its_owner(self):
        SaveReceipt.objects.create(user=self.other,action='Other family private action')
        self.assertNotContains(self.client.get('/saved/'),'Other family private action')
        self.assertContains(self.client.get('/saved/'),'No saves confirmed yet')
    def test_later_success_updates_a_single_receipt(self):
        self.client.post('/collections/new/',{'name':'One','cover_style':'crystal'})
        first=SaveReceipt.objects.get(user=self.user).saved_at
        self.client.post('/collections/new/',{'name':'Two','cover_style':'midnight'})
        self.assertEqual(SaveReceipt.objects.filter(user=self.user).count(),1)
        self.assertGreaterEqual(SaveReceipt.objects.get(user=self.user).saved_at,first)
    def test_failed_form_preserves_the_previous_confirmed_save(self):
        self.client.post('/collections/new/',{'name':'Original','cover_style':'crystal'})
        before=SaveReceipt.objects.get(user=self.user).saved_at
        self.client.post('/collections/new/',{'name':'','cover_style':'crystal'})
        self.assertEqual(SaveReceipt.objects.get(user=self.user).saved_at,before)
    def test_receipt_rolls_back_with_failed_transaction(self):
        request=RequestFactory().post('/collections/new/')
        request.user=self.user;request.session={};request._messages=FallbackStorage(request)
        with self.assertRaises(ValueError):
            with transaction.atomic():
                saved_success(request,'Uncommitted write')
                raise ValueError('Rollback')
        self.assertFalse(SaveReceipt.objects.filter(user=self.user).exists())
    def test_guest_does_not_receive_another_users_status(self):
        SaveReceipt.objects.create(user=self.user,action='Private save marker')
        self.client.logout()
        self.assertNotContains(self.client.get('/'),'Private save marker')
        self.assertNotContains(self.client.get('/'),'id="saved-data-status"')
