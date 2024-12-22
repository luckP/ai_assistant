# Use the official Python image
FROM python:3.12

# Set the working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire gRPC server codebase into the container
COPY . .

# Expose the gRPC port (e.g., 50051)
EXPOSE 50051

# Start the gRPC server
CMD ["python", "server.py"]
