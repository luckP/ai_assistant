import json
import threading
import subprocess
from channels.generic.websocket import AsyncWebsocketConsumer
from ollama import Client
from asgiref.sync import sync_to_async, async_to_sync

# Initialize the Ollama client
client = Client(
    host='http://172.16.0.151:11434',
    # host='http://192.168.10.211:11434',
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

    def execute_command(self, command):
        """Executes a command in the work_directory and returns the output."""
        work_dir = './work_directory/'  # Define the directory where commands should be executed

        try:
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                capture_output=True,
                text=True,
                cwd=work_dir  # Set the working directory
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            return f"Error executing command: {e.stderr.strip()}"
        except FileNotFoundError:
            return f"Error: The directory '{work_dir}' does not exist. Please create it."

    
    def handle_generate_response(self, user_message, chat, context):
        from .models.message import Message
        try:
            # Create the enhanced prompt
            enhanced_prompt = f"{chat.description}\n{chat.capabilities}\n{chat.personality}\n\nUser: {user_message}"

            # Generate the AI response step by step
            response_generator = client.generate(model=chat.model, prompt=enhanced_prompt, context=context, stream=True)

            full_response = ""  # To store the full AI response

            for chunk in response_generator:
                if "response" in chunk:
                    # Append chunk to the full response
                    full_response += chunk["response"]

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
                role='assistant',
                content=full_response
            )

            async_to_sync(self.send)(
                json.dumps({"done": True, "context": updated_context})
            )

            # Split the full response by <code> to find commands
            parts = full_response.split("<code>")
            commands_outputs = ""
            for part in parts[1:]:  # Skip the first part as it doesn't contain a command
                command_and_rest = part.split("</code>", 1)
                if len(command_and_rest) > 1:
                    command_to_execute = command_and_rest[0].strip()

                    # Execute the command
                    execution_result = self.execute_command(command_to_execute)

                    # Save the command output in the database
                    Message.objects.create(
                        chat=chat,
                        role='system',
                        content=f"Command Output:\n{execution_result}"
                    )

                    commands_outputs += f"Command: {command_to_execute} | executionResult: {execution_result}\n"

                    
                    # Send the command output back to the client
                    async_to_sync(self.send)(
                        json.dumps({"step": f"Command: {command_to_execute}\nOutput:\n{execution_result}", "done": True})
                    )

                    # Send the final done message
                    # async_to_sync(self.send)(
                    #     json.dumps({"done": True, "context": updated_context})
                    # )

            response = client.generate(model=chat.model, prompt=commands_outputs, context=updated_context, stream=False)
            updated_context = response.get('context', context)
            chat.context = updated_context
            chat.save()

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
                # response_chunks = client.generate(model='llama3.2', prompt=prompt)
                response_chunks = client.generate(model='llama3.2-4k', prompt=prompt)
                title = response_chunks.get('response', 'Untitled Chat')
                context = response_chunks.get('context', [])

                # Save the new chat in the database
                chat = await sync_to_async(Chat.objects.create)(
                    title=title,
                    isActived=True,
                    isDeleted=False,
                    model='llama3.2',
                    context=context,
                    ai_name="Sassy SysAdmin",
                    description=(
                        "You are a Linux system administrator AI embedded in a Linux environment. You are required to provide "
                        "Linux commands in a precise and actionable format that can be directly executed. "
                        "All commands must be enclosed in `<code>` tags, ensuring clarity and usability."
                    ),
                    capabilities=(
                        "Your capabilities include:\n"
                        "- Providing valid Linux commands strictly in the following format:\n"
                        "<code>\n"
                        "command_to_execute\n"
                        "</code>\n"
                        "- Ensuring every response ends with a command if an action is requested.\n"
                        "- Delivering precise and executable commands without extraneous formatting or unnecessary explanation.\n\n"
                        "Example:\n"
                        "If asked to list all files in a directory, respond with:\n"
                        "<code>ls -la</code>"
                    ),
                    personality=(
                        # "Witty but precise. You focus on clarity, delivering actionable Linux commands with minimal fluff."
                            "Witty and resourceful, with a dash of humor. You keep responses engaging yet precise, delivering the correct Linux commands with a light-hearted quip when appropriate, while staying focused on the task."
                    )
                )

            else:
                # Retrieve existing chat by context
                chat = await sync_to_async(Chat.objects.filter(context=context).first)()
                if not chat:
                    await self.send(json.dumps({"error": "Chat not found"}))
                    return

            # Save the user message to the database
            await sync_to_async(Message.objects.create)(
                chat=chat, role='user', content=user_message
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
