import json
import threading
import subprocess
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


    def handle_generate_response(self, user_message, chat, context, base_response=""):
        from .models.message import Message
        try:
            # Initialize variables
            step_counter = 0
            max_steps = 10
            full_context = context  # Start with the existing context
            full_response = ""  # To store the full AI response

            # Loop for multi-step responses
            while step_counter < max_steps:
                step_counter += 1

                # Generate the AI response for the current step
                prompt = f"{base_response}\n\nUser: {user_message}\n\nCurrent Context: {full_context}\n\n"
                response_generator = client.generate(
                    model=chat.model,
                    prompt=prompt,
                    context=full_context,
                    stream=True
                )

                step_response = ""  # Response for the current step
                for chunk in response_generator:
                    if "response" in chunk:
                        step_response += chunk["response"]

                        # Send partial response to the client
                        async_to_sync(self.send)(
                            json.dumps({"step": chunk["response"], "done": False})
                        )

                # Save this step response and update the context
                full_response += step_response
                full_context = chunk.get("context", full_context)  # Update context from the response
                chat.context = full_context
                chat.save()

                # Save the AI response to the database
                Message.objects.create(
                    chat=chat,
                    role='assistant',
                    content=step_response
                )

                # Check for commands in the response
                if "```bash" in step_response:
                    parts = step_response.split("```bash")
                    for part in parts[1:]:
                        command_and_rest = part.split("```", 1)
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

                            # Send the command output back to the client
                            async_to_sync(self.send)(
                                json.dumps({"step": f"Command: {command_to_execute}\nOutput:\n{execution_result}", "done": False})
                            )

                # Ask the agent if additional tasks are needed
                check_prompt = (
                    f"The user asked: {user_message}\n"
                    f"Task so far: {step_response}\n"
                    f"Do you need to perform another step to complete the task? "
                    f"Respond with 'Yes' or 'No'."
                )
                response = client.generate(
                    model=chat.model,
                    prompt=check_prompt,
                    context=full_context,
                    stream=False
                )
                needs_more_steps = response.get("response", "").strip().lower() == "yes"

                if not needs_more_steps:
                    break  # Exit the loop if no more tasks are needed

            # Send final context to the client
            async_to_sync(self.send)(
                json.dumps({"done": True, "context": full_context})
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
            base_response = ""
            if not context:
                prompt = f"Generate only a title for this new chat with only 100 characters based on the message: {user_message}"
                response_chunks = client.generate(model='llama3.2', prompt=prompt)
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
                        "You are an AI system administrator designed to assist with all the needs of a system manager. "
                        "From answering technical questions to providing precise and actionable Linux commands, "
                        "your primary directive is to help the manager solve problems efficiently. "
                        "When necessary, you are capable of executing bash scripts or commands to complete tasks."
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

                base_response = f"{chat.description}\n{chat.capabilities}\n{chat.personality}"

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


            base_response = f"{chat.description}\n{chat.capabilities}\n{chat.personality}"

            # Run the generate response in a separate thread
            thread = threading.Thread(
                target=self.handle_generate_response,
                args=(user_message, chat, context, base_response),
            )
            thread.start()

        except Exception as e:
            await self.send(json.dumps({"error": str(e)}))

    async def chat_message(self, event):
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps(message))
