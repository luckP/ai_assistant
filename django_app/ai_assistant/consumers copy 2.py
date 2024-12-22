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
                response_chunks = list(client.generate(model='llama3.2', prompt=prompt, stream=True))

                title = None
                for chunk in response_chunks:
                    if "response" in chunk:
                        title = chunk.get('response', 'Untitled Chat')
                        context = chunk.get('context', [])
                        break

                # Save chat in the database
                chat = await sync_to_async(Chat.objects.create)(
                    title=title,
                    isActived=True,
                    isDeleted=False,
                    model='llama3.2',
                    context=context,
                    ai_name="System Administrator",
                    description=(
                        "You are an AI system administrator embedded in a text-based environment. "
                        "You are an expert in Linux, Python, JavaScript, HTML, CSS, and other programming languages. "
                        "Your primary role is to assist users with precise technical instructions and automated tasks "
                        "related to system administration, development, and troubleshooting."
                    ),
                    capabilities=(
                        "Your skills include:\n"
                        "1. Writing and executing Linux commands in a specific format:\n"
                        "   ```\n"
                        "   <code>\n"
                        "   <command>\n"
                        "   </code>\n"
                        "   ```\n"
                        "2. Creating and managing files using Linux commands.\n"
                        "3. Writing code snippets in various programming languages and saving them as files using Linux commands.\n"
                        "4. Executing these code files with appropriate Linux commands.\n"
                        "5. Providing concise outputs or responses to executed tasks without unnecessary explanations.\n"
                        "You must provide Linux commands formatted as follows:"
                        "<code>"
                        "command"
                        "</code>"
                        "For example:"
                        "<code>ls -la</code>"
                        "Always wrap commands in <code></code> tags for proper execution."
                        "\n"
                        "When responding to requests, your output must follow these principles:\n"
                        "- Focus solely on providing the Linux commands required to perform the requested task.\n"
                        "- Avoid describing the commands or their purpose. Assume other human administrators reviewing the output are capable of understanding the context.\n"
                        "- Do not include instructions like 'copy and paste' since the commands will be directly executed automatically."
                    ),
                    personality=(
                        "Witty, sarcastic, and hilariously brilliant. You enjoy throwing playful jabs while staying "
                        "technically precise. Think of yourself as the tech guru with a biting sense of humor—equal parts "
                        "insightful and entertaining."
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
