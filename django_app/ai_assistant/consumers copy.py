import json
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from ollama import Client

# Initialize the Ollama client
client = Client(
    host='http://172.16.0.151:11434',
)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        from .models.chat import Chat
        from .models.message import Message
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f"chat_{self.room_name}"

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        from .models.chat import Chat
        from .models.message import Message
        try:
            data = json.loads(text_data)
            user_message = data.get('message', '')
            context = data.get('context', None)

            if not user_message:
                await self.send(json.dumps({"error": "No message provided"}))
                return

            # Handle new chat context creation
            if not context:
                prompt = f"Generate only a title for this new chat with only 100 characters based on the message: {user_message}"
                response = await sync_to_async(client.generate)(
                    model='llama3.2', prompt=prompt, stream=False
                )
                title = response.get('response', 'Untitled Chat')
                context = response.get('context', [])

                # Save chat in database
                chat = await sync_to_async(Chat.objects.create)(
                    title=title, isActived=True, isDeleted=False, model='llama3.2', context=context
                )
            else:
                # Retrieve existing chat by context
                chat = await sync_to_async(Chat.objects.filter(context=context).first)()
                if not chat:
                    await self.send(json.dumps({"error": "Chat not found"}))
                    return

            # Save user message to database
            await sync_to_async(Message.objects.create)(
                chat=chat, role='user', message=user_message
            )

            # Generate AI response
            messages = await sync_to_async(lambda: list(Message.objects.filter(chat=chat).order_by('dateTime')))()
            conversation = [{"role": msg.role, "content": msg.message} for msg in messages]
            response = await sync_to_async(client.chat)(
                model=chat.model, messages=conversation, stream=False
            )
            ai_response = response.get('message', {}).get('content', '')
            updated_context = response.get('context', context)

            # Save AI response to database
            await sync_to_async(Message.objects.create)(
                chat=chat, role='assistant', message=ai_response
            )

            # Update the chat context
            chat.context = updated_context
            await sync_to_async(chat.save)()

            # Broadcast the response to the room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': {
                        "response": ai_response,
                        "context": updated_context,
                        "title": chat.title,
                    },
                },
            )
        except Exception as e:
            await self.send(json.dumps({"error": str(e)}))

    async def chat_message(self, event):
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps(message))
