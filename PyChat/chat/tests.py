from django.test import TestCase

from .models import Conversation


class ConversationLegacyIdCompatibilityTests(TestCase):
    def test_legacy_numeric_string_ids_can_be_saved_and_retrieved(self):
        conversation = Conversation.objects.create(id='1', name='Legacy chat')

        self.assertEqual(str(conversation.pk), '1')
        self.assertEqual(Conversation.objects.get(pk='1').name, 'Legacy chat')
