from django.db import models
from django.utils.timezone import now

class Chat(models.Model):
    id = models.AutoField(primary_key=True)
    dateTime = models.DateTimeField(default=now)
    title = models.CharField(max_length=255)
    isActived = models.BooleanField(default=True)
    isDeleted = models.BooleanField(default=False)
    model = models.CharField(max_length=100)
    context = models.JSONField(default=list)
    
    # New fields to describe the AI
    ai_name = models.CharField(max_length=100, default="AI Assistant")  # Name of the AI
    description = models.TextField(blank=True, null=True)  # Short description of the AI's role
    capabilities = models.TextField(blank=True, null=True)  # Description of what the AI can do
    personality = models.CharField(max_length=255, blank=True, null=True)  # Personality traits of the AI

    def __str__(self):
        return self.title
