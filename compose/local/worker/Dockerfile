# Use the official Python image
FROM python:3.13-slim

# Set the working directory
WORKDIR /app

# Copy project files to the container
COPY . /app

# Install dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# # Run the Django development server
CMD ["celery", "-A", "image_processing_service", "worker", "-l", "info"]