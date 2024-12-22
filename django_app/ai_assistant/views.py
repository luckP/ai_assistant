from django.shortcuts import render
from django.http import JsonResponse
import requests
import json
from .models.chat import Chat
from .models.message import Message
from ollama import Client

# Initialize the Ollama client
client = Client(
    host='http://172.16.0.151:11434',
    # headers={'x-some-header': 'some-value'}  # Customize headers if needed
)


def index(request):
    return render(request, 'index.html')


def chat_view(request):
    if request.method == "GET":
        return render(request, 'chat.html')

    if request.method == "POST":
        try:
            # Parse the JSON request body
            data = json.loads(request.body)
            user_message = data.get('message', '')
            context = data.get('context', None)

            if not user_message:
                return JsonResponse({"error": "No message provided"}, status=400)

            if not context:
                # No context: create a new chat
                prompt = "Generate only a title for this new chat with only 100 characters based on the message: " + user_message
                response = client.generate(model='llama3.2', prompt=prompt, stream=False)
                title = response.get('response', 'Untitled Chat')
                context = response.get('context', [])

                # Create the new chat
                chat = Chat.objects.create(
                    title=title,
                    isActived=True,
                    isDeleted=False,
                    model='llama3.2',
                    context=context
                )

            else:
                # Existing context: retrieve the chat and add a new message
                chat = Chat.objects.filter(context=context).first()
                if not chat:
                    return JsonResponse({"error": "Chat not found"}, status=404)

            # Add the user message
            Message.objects.create(
                chat=chat,
                role='user',
                message=user_message
            )

            # Generate a response
            messages = Message.objects.filter(chat=chat).order_by('dateTime')
            conversation = [{"role": msg.role, "content": msg.message} for msg in messages]
            response = client.chat(model=chat.model, messages=conversation, stream=False)
            ai_response = response.get('message', {}).get('content', '')
            updated_context = response.get('context', context)

            # Add the AI response
            Message.objects.create(
                chat=chat,
                role='assistant',
                message=ai_response
            )

            # Update the chat context
            chat.context = updated_context
            chat.save()

            return JsonResponse({
                "response": ai_response,
                "context": updated_context,
                "title": chat.title
            })

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)