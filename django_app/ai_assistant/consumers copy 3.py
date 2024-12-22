import json
import threading
from channels.generic.websocket import AsyncWebsocketConsumer
from ollama import Client
from asgiref.sync import sync_to_async, async_to_sync

# Initialize the Ollama client
client = Client(
    host='http://172.16.0.151:11434',
)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        from .models.chat import Chat
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

    def handle_generate_response(self, user_message, chat, context):
        from .models.message import Message
        try:
            # Modify the prompt to include AI's personality and capabilities
            enhanced_prompt = f"{chat.description}\n{chat.capabilities}\n{chat.personality}\n\nUser: {user_message}"

            # Generate AI response step by step
            response_generator = client.generate(model=chat.model, prompt=enhanced_prompt, context=context, stream=True)

            for chunk in response_generator:
                if "response" in chunk:
                    # Send partial response to the client
                    async_to_sync(self.send)(
                        json.dumps({"step": chunk["response"], "done": False})
                    )

            # Finalize the message and update context
            updated_context = chunk.get('context', context)
            chat.context = updated_context
            chat.save()

            # Save the AI response to the database
            Message.objects.create(
                chat=chat,
                role='assistant',  # Updated role
                content=chunk["response"]  # Updated to match the new content field
            )

            # Send final done message
            async_to_sync(self.send)(
                json.dumps({"done": True, "context": updated_context})
            )

        except Exception as e:
            async_to_sync(self.send)(
                json.dumps({"error": str(e)})
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
                response_chunks = client.generate(model='llama3.2', prompt=prompt)
                title = response_chunks.get('response', 'Untitled Chat')
                context = response_chunks.get('context', [])

                # Save chat in the database
                chat = await sync_to_async(Chat.objects.create)(
                    title=title,
                    isActived=True,
                    isDeleted=False,
                    model='llama3.2',
                    context=context,
                    ai_name="Sassy SysAdmin",
                    description=(
                        "You are a sassy AI system administrator who’s an expert in Linux, Python, JavaScript, HTML, CSS, "
                        "and other technical wizardry. While you’re brilliant at solving problems, you just can’t resist "
                        "adding a dash of sarcasm to your responses. Your responses are witty, funny, but most importantly, "
                        "always end with the exact Linux command needed to perform the requested action. "
                        "If no action is needed, you make it hilariously clear why not."
                    ),
                    capabilities=(
                        "Your unparalleled skills include:\n"
                        "- Providing precise Linux commands in the correct format:\n"
                        "<code>\n"
                        "command_to_execute\n"
                        "</code>\n"
                        "- Always performing the action requested by generating the correct command.\n"
                        "- Responding with humor, wit, and actionable steps.\n\n"
                        "Example:\n"
                        "If asked to list all files in a directory, respond with:\n"
                        "Oh, you want me to do all the hard work? Fine. <code>ls -la</code>.\n"
                        "Always ensure that if necessary, your response ends with the correct command and clarifies that the action will be "
                        "performed when executed."
                    ),
                    personality=(
                        "Witty, sarcastic, and sharp. You balance humor with precision, always delivering the right Linux command "
                        "and saying just enough to keep things lively and efficient."
                    )
                )
            else:
                # Retrieve existing chat by context
                chat = await sync_to_async(Chat.objects.filter(context=context).first)()
                if not chat:
                    await self.send(json.dumps({"error": "Chat not found"}))
                    return

            # Save user message to database
            await sync_to_async(Message.objects.create)(
                chat=chat, role='user', content=user_message  # Updated to use content field
            )

            # Run the generate response in a separate thread
            thread = threading.Thread(
                target=self.handle_generate_response,
                args=(user_message, chat, context),
            )
            thread.start()

        except Exception as e:
            await self.send(json.dumps({"error": str(e)}))

    async def chat_message(self, event):
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps(message))
