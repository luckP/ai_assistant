from django.test import TestCase
from apps.chat.models import Chat, Message

class ChatModelTest(TestCase):
    def setUp(self):
        self.chat = Chat.objects.create(
            title="Test Chat",
            model="llama3.2",
            context=[1, 2, 3]
        )

    def test_chat_creation(self):
        self.assertEqual(self.chat.title, "Test Chat")
        self.assertTrue(self.chat.isActived)
        self.assertFalse(self.chat.isDeleted)

class MessageModelTest(TestCase):
    def setUp(self):
        self.chat = Chat.objects.create(title="Test Chat", model="llama3.2")
        self.message = Message.objects.create(
            chat=self.chat,
            role="user",
            message="Hello, World!"
        )

    def test_message_creation(self):
        self.assertEqual(self.message.chat.title, "Test Chat")
        self.assertEqual(self.message.role, "user")
        self.assertEqual(self.message.message, "Hello, World!")
