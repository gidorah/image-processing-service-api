# Use the official Python image
FROM python:3.13-slim

# Set the working directory
WORKDIR /app

# Copy project files to the container
COPY . /app

# Install dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Expose the port Django will run on
EXPOSE 8000

# # Run the Django development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]