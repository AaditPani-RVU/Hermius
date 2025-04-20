# Use the official Python image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Copy only requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install eventlet for Flask-SocketIO
RUN pip install eventlet python-dotenv

# Copy the rest of the application code
COPY . .

# Expose the port Flask will run on
EXPOSE 5000

# Start the app with eventlet (recommended for Flask-SocketIO)
CMD ["python", "main.py"]
