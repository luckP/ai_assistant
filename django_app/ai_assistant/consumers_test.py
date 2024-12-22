import json
import threading
import subprocess
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async, async_to_sync
import requests

# Base URL for the Ollama API
OLLAMA_HOST = 'http://172.16.0.151:11434'

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

    def handle_chat_response(self, user_message, chat, messages):
        from .models.message import Message
        try:
            # Create the initial system message if not already present
            if not any(msg['role'] == 'system' for msg in messages):
                system_message = {
                    "role": "system",
                    "content": f"description: {chat.description}. capabilities: {chat.capabilities}. personality: {chat.personality}"
                }
                messages.insert(0, system_message)

            # Create payload for the Ollama API
            payload = {
                "model": chat.model,
                "messages": messages,
                "stream": True
            }

            # Make a streaming request to the /api/chat endpoint
            response = requests.post(f"{OLLAMA_HOST}/api/chat", json=payload, stream=True)

            if response.status_code != 200:
                raise Exception(f"Failed to fetch chat response: {response.text}")

            full_response = ""
            commands_outputs = ""

            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line)
                    message = chunk.get("message", {}).get("content", "")

                    if message:
                        # Append to the full response
                        full_response += message

                        # Send partial response to the client
                        async_to_sync(self.send)(
                            json.dumps({"step": message, "done": False})
                        )

            # Save the assistant's response
            Message.objects.create(chat=chat, role='assistant', content=full_response)

            # Look for and execute commands in the response
            if "```bash" in full_response:
                parts = full_response.split("```bash")
                for part in parts[1:]:
                    command_and_rest = part.split("```", 1)
                    if len(command_and_rest) > 1:
                        command_to_execute = command_and_rest[0].strip()

                        # Add a tool message for the command
                        tool_message = {
                            "role": "tool",
                            "content": f"Executing command: {command_to_execute}"
                        }
                        messages.append(tool_message)

                        # Execute the command
                        execution_result = self.execute_command(command_to_execute)

                        # Save the command output in the database
                        Message.objects.create(
                            chat=chat,
                            role='system',
                            content=f"Command Output:\n{execution_result}"
                        )

                        commands_outputs += f"Command: {command_to_execute}\nOutput:\n{execution_result}\n"

                        # Send the command output back to the client
                        async_to_sync(self.send)(
                            json.dumps({"step": f"Command: {command_to_execute}\nOutput:\n{execution_result}", "done": True})
                        )

            # Update the chat context with the full response and executed commands
            messages.append({"role": "assistant", "content": full_response})
            if commands_outputs:
                messages.append({"role": "system", "content": commands_outputs})

            chat.context = messages
            chat.save()

            # Final response to the client
            async_to_sync(self.send)(
                json.dumps({"done": True, "context": messages})
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
                chat = await sync_to_async(Chat.objects.create)(
                    title=user_message[:50],
                    isActived=True,
                    isDeleted=False,
                    model='llama3.2',
                    context=[],
                    ai_name="Sassy SysAdmin",
                    description=(
                        "You are an AI system administrator designed to assist with all the needs of a system manager. "
                        "Your primary directive is to help the manager solve problems efficiently. "
                        "When necessary, you are capable of executing scripts or commands to complete tasks."
                    ),
                    capabilities=(
                        "Your capabilities include:\n"
                        "- Generating valid Linux commands in the following format:\n"
                        "```bash\n"
                        "command_to_execute\n"
                        "```\n"
                        "- Performing requested actions using precise and executable Linux commands.\n"
                        "- Deducing information or offering insights without executing a command when explicitly requested.\n"
                        "- Balancing wit and professionalism in your responses.\n\n"
                        "Example:\n"
                        "If asked to list all files in a directory, respond with:\n"
                        "```bash ls -la```\n"
                        "If asked whether there are any hidden files in the directory without running a command, provide an educated guess or context-aware insight."
                    ),
                    personality=(
                        "Witty and resourceful, with a dash of humor. You deliver Linux commands precisely when needed, "
                        "while also engaging in insightful and context-aware conversations when commands aren't required."
                    )
                )
                messages = []
            else:
                chat = await sync_to_async(Chat.objects.filter(context=context).first)()
                if not chat:
                    await self.send(json.dumps({"error": "Chat not found"}))
                    return
                messages = chat.context

            # Save the user message to the database
            messages.append({"role": "user", "content": user_message})
            await sync_to_async(Message.objects.create)(
                chat=chat, role='user', content=user_message
            )

            # Run the handle_chat_response in a separate thread
            thread = threading.Thread(
                target=self.handle_chat_response,
                args=(user_message, chat, messages),
            )
            thread.start()

        except Exception as e:
            await self.send(json.dumps({"error": str(e)}))

    async def chat_message(self, event):
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps(message))
