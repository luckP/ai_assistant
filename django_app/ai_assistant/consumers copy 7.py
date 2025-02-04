from channels.generic.websocket import AsyncWebsocketConsumer
from .Agents import AIAgent, PythonAgent, ShellAgent, TaskManager


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.task_manager = TaskManager(self)
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f"chat_{self.room_name}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            await self.task_manager.handle_message(data)
        except Exception as e:
            await self.send(json.dumps({"error": str(e)}))
