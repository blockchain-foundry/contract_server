from django.utils import timezone
import json
from django.test import TestCase
from events.models import Watch
import sha3
import binascii

TEST_KEY = "TEST_KEY"


class ModelWatchTestCase(TestCase):

    def setUp(self):
        Watch.objects.get_or_create(
            multisig_address="test_multisig_address",
            key=TEST_KEY,
            subscription_id="test")

    def test_get_hashed_key(self):
        watch = Watch.objects.get(key=TEST_KEY)

        k = sha3.keccak_256()
        k.update(watch.key.encode())
        self.assertEqual(watch.hashed_key, k.hexdigest())

    def test_is_expired(self):
        watch = Watch.objects.get(key=TEST_KEY)
        self.assertEqual(watch.is_expired, False)

        watch.created = watch.created + timezone.timedelta(minutes=20)
        self.assertEqual(watch.is_expired, True)
