from channels.generic.websocket import AsyncWebsocketConsumer
from ai_assistant.Agents import TaskManager
from asgiref.sync import sync_to_async
import json


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Initialize TaskManager
        self.task_manager = TaskManager(self)
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f"chat_{self.room_name}"

        # Add this WebSocket connection to the group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Remove this WebSocket connection from the group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        from ai_assistant.models import Message
        try:
            data = json.loads(text_data)
            user_message = data.get("message", "")
            context = data.get("context", None)

            if not user_message:
                await self.send(json.dumps({"error": "No message provided"}))
                return

            # Retrieve or create a Chat object
            chat = await self.get_or_create_chat(context, user_message)

            # Save the user message to the database
            await sync_to_async(Message.objects.create)(
                chat=chat,
                role="user",
                content=user_message
            )

            # Pass the Chat object and user message to TaskManager
            self.task_manager.handle_message(data, chat)
        except Exception as e:
            await self.send(json.dumps({"error": f"receive error: {str(e)}"}))

    @sync_to_async
    def get_or_create_chat(self, context, user_message):
        from ai_assistant.models import Chat
        """Get or create a Chat instance."""
        if context:
            chat = Chat.objects.filter(context=context).first()
            if chat:
                return chat

        # Create a new Chat if no context is found
        return Chat.objects.create(
            title=f"Chat for: {user_message[:50]}",
            model="llama3.2-4k",
            context=[],
            ai_name="TARS-like AI",
            description="A witty and professional AI crew member.",
            capabilities="Handles tasks, answers queries, and performs logical reasoning with dry humor.",
            personality="Witty, resourceful, logical, with adjustable humor settings.",
            humor_level=85
        )
