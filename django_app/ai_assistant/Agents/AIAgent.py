from ollama import Client

class AIAgent:
    def __init__(self):
        self.client = Client(host='http://172.16.0.151:11434')

    def generate_response(self, user_message, chat):
        """
        Generate a response based on the chat object.
        
        Args:
            user_message (str): The user's message.
            chat (Chat): The chat object containing personality, context, humor_level, etc.
        
        Yields:
            str or dict: Partial responses or the final context.
        """
        # Extract properties from the chat object
        humor_level = chat.humor_level if hasattr(chat, 'humor_level') else 75
        personality = chat.personality or "Witty, resourceful, logical, with adjustable humor settings."
        description = chat.description or "A helpful AI assistant."
        context = chat.context or []

        # Build the prompt
        humor = f"Humor level: {humor_level}%. Be witty and professional."
        prompt = f"""
        Personality: {personality}. {humor}
        Description: {description}
        Task: {user_message}
        Context: {context}
        Provide responses that are precise, actionable, and optionally humorous based on the humor level.
        """

        # Stream the response from the AI model
        response_generator = self.client.generate(model=chat.model, prompt=prompt, context=context, stream=True)
        for chunk in response_generator:
            if "response" in chunk:
                yield chunk["response"]

        # Return the final context if provided by the model
        yield {"context": chunk.get("context", context), "done": True}
