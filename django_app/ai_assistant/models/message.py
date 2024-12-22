from django.db import models
from django.utils.timezone import now
from .chat import Chat

class Message(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),  # Renamed to align with Ollama's role terminology
        ('system', 'System'),
    ]

    id = models.AutoField(primary_key=True)
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()  # Renamed to 'content' to better match the JSON schema
    timestamp = models.DateTimeField(default=now)  # Renamed to 'timestamp' for clarity

    class Meta:
        ordering = ['timestamp']  # Ensure messages are always retrieved in chronological order

    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."
