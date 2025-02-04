import threading
import json
from ai_assistant.Agents.ShellAgent import ShellAgent
from ai_assistant.Agents.PythonAgent import PythonAgent
from ai_assistant.Agents.AIAgent import AIAgent
from asgiref.sync import async_to_sync
from ollama import Client


class TaskManager:
    def __init__(self, consumer):
        self.consumer = consumer
        self.shell_agent = ShellAgent()
        self.python_agent = PythonAgent()
        self.ai_agent = AIAgent()
        self.client = Client(host='http://172.16.0.151:11434')

    def handle_message(self, data, chat):
        thread = threading.Thread(target=self._handle_message_thread, args=(data, chat))
        thread.start()

    def _handle_message_thread(self, data, chat):
        from ai_assistant.models import Message
        try:
            user_message = data.get("message", "")
            context = chat.context

            if not user_message:
                self._send_to_client({"error": "No message provided"})
                return

            # Stream AI response

            tasks = self.extract_tasks(user_message, chat)
            self._send_to_client({"done": True, "step": "test"})

            full_response = ""
            for chunk in self.ai_agent.generate_response(user_message, chat):
                if isinstance(chunk, dict) and chunk.get("done"):
                    chat.context = chunk.get("context")
                    chat.save()
                else:
                    self._send_to_client({"step": chunk, "done": False})
                    full_response += chunk

            # Save the assistant's response to the database
            Message.objects.create(chat=chat, role="assistant", content=full_response)

            # Send completion message
            self._send_to_client({"done": True, "context": chat.context})
            self._send_to_client({"done": True, "step": str(tasks), "context": chat.context})
            # for task in tasks:
            #     self._send_to_client({"done": True, "step": task, "context": chat.context})
        except Exception as e:
            self._send_to_client({"error": str(e)})

    def _send_to_client(self, message):
        async_to_sync(self.consumer.send)(json.dumps(message))

    def extract_tasks(self, user_message, chat):
        """
        Use the AI client to extract tasks from the user's message.

        Args:
            user_message (str): The user's input message.
            chat (Chat): The chat object for context.

        Returns:
            list: A list of extracted tasks, or an empty list if no actionable tasks are found.
        """
        prompt = f"""
        You are a task extraction assistant. Break down the following user request into actionable tasks. The tasks list should be empty ([]) if the user request does not require any action.
        Each task should be clearly labeled as either 'shell' (for command-line operations) or 'python' (for Python code).

        Example input 1:
        "Create a file named test.py with 'hello world', execute this file, then remove it."
        
        Example output:
        [
            {{"type": "shell", "task": "create a new file named test.py"}},
            {{"type": "python", "task": "write a 'hello world' example and save it in test.py"}},
            {{"type": "shell", "task": "execute the python file"}},
            {{"type": "shell", "task": "remove the file"}}
        ]

        Example input 2:
        "Hello chat, how are you?"

        Example output:
        []

        Example input 3:
        "Write Python code to calculate the sum of a list of numbers and print the result."

        Example output:
        [
            {{"type": "python", "task": "write Python code to calculate the sum of a list of numbers and print the result"}}
        ]

        Example input 4:
        "Create a folder named 'data' and move all CSV files into it."

        Example output:
        [
            {{"type": "shell", "task": "create a folder named 'data'"}},
            {{"type": "shell", "task": "move all CSV files into the 'data' folder"}}
        ]


        

        User Request: {user_message}
        """

        # Use AI to extract tasks
        response_task_generator = self.client.generate(model=chat.model, prompt=prompt, stream=False)
        # tasks = []

        try:
            tasks = json.loads(response_task_generator.get('response'))


        except Exception as e:
            tasks = []
            self._send_to_client({"error": str(e)}) 

        return tasks

    def execute_task(self, task):
        """
        Execute a single task based on its type.

        Args:
            task (dict): A task with keys 'type' and either 'command' or 'code'.

        Returns:
            str: Result of the task execution.
        """
        try:
            if task["type"] == "shell":
                return self.shell_agent.execute(task["command"])
            elif task["type"] == "python":
                return self.python_agent.execute(task["code"])
            else:
                return f"Unknown task type: {task['type']}"
        except Exception as e:
            return f"Error executing task: {str(e)}"

    def _send_to_client(self, message):
        async_to_sync(self.consumer.send)(json.dumps(message))
