# Use the official Python 3.12 image as the base image
FROM python:3.12

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt requirements.txt

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project files into the container
COPY . .

# Set environment variable for Django settings
ENV DJANGO_SETTINGS_MODULE=ai_assistant.settings

# Add PYTHONPATH to the Dockerfile
ENV PYTHONPATH=/app

# Expose the port the app runs on
EXPOSE 8000

# Run the application with Daphne
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "ai_assistant.asgi:application"]
