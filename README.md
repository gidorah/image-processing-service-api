# Image Processing Service API

This repository contains the backend for an image processing service, built with Django and Django REST Framework (DRF). It allows users to upload images, perform various transformations, and retrieve images in different formats.

## Project Structure

The project is structured as follows:

```
image-processing-service-api/   # Project root directory
├── api/                # Django app for the API
│   ├── ...
│
├── image_processor/     # Django app for image processing
│   ├── ...
│
├── image_processing_service/  # Django project settings directory
│   ├── ...
│
├── manage.py           # Django management script
├── requirements.txt    # Project dependencies
├── .env                # Environment variables (KEEP THIS OUT OF VERSION CONTROL)
├── .gitignore          # Files and directories to ignore in Git
├── docker-compose.yml  # (Optional) For local development with Docker
├── Dockerfile          # (Optional) For building a Docker image
└── README.md           # This file
└── celery.py            # celery configurations
```

*   **`api/`:**  Handles API requests and responses, authentication, and serialization.
*   **`image_processor/`:**  Contains the core image processing logic, including models, Celery tasks, and utility functions.
*   **`image_processing_service/`:** Contains project-wide settings (database, Celery, S3, etc.).

## Features

*   **User Authentication:**
    *   User registration and login.
    *   JWT (JSON Web Token) authentication for API access.
*   **Image Management:**
    *   Upload images.
    *   Retrieve images.
    *   List uploaded images (with pagination).
*   **Image Transformations:**
    *   Resize
    *   Crop
    *   Rotate
    *   Watermark
    *   Flip
    *   Mirror
    *   Compress
    *   Change format (JPEG, PNG, etc.)
    *   Apply filters (grayscale, sepia, etc.)
    *   Asynchronous and Synchronous transformations
*   **Scalability:**
    *   Uses Celery for asynchronous task processing.
    *   Uses Amazon S3 for efficient image storage.
* **API Versioning:**
    * Uses URI path versioning
*   **Caching:**
    *  [To be implemented: Caching mechanism for transformed images (e.g., Redis, CDN).]
*   **Rate Limiting:**
    *  [To be implemented: Rate limiting for image transformations to prevent abuse.]
* **Error Handling:**
    * Provides appropriate HTTP status and error responses.

## Technologies Used

*   **Python:** Programming language.
*   **Django:** Web framework.
*   **Django REST Framework (DRF):**  Toolkit for building Web APIs.
*   **Celery:** Distributed task queue for asynchronous processing.
*   **Pillow:** Image processing library.
*   **PostgreSQL:** Database.
*   **Amazon S3:** Object storage for images.
*   **Redis:**  [To be implemented: In-memory data store (for caching and Celery broker/backend).]
* **JWT:** JSON web token for authentication
* **Sentry:** For error tracking
* **ELK:** For logging

## Setup (Local Development)

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd image-processing-service-api
    ```

2.  **Create a virtual environment:**

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Linux/macOS
    venv\Scripts\activate    # On Windows
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**

    *   Create a `.env` file in the project root.
    *   Add necessary environment variables (see `.env.example` or the section below for required variables).

5.  **Configure PostgreSQL:**

    *   Make sure PostgreSQL is installed and running.
    *   Create a database for the project.
    *   Update the database settings in `image_processing_service/settings.py` (using environment variables from `.env`).

6.  **Configure Redis:**
   * Install and configure Redis

7. **Configure S3**
    * Create S3 bucket and configure credentials.

8.  **Run migrations:**

    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

9.  **Run the development server:**

    ```bash
    python manage.py runserver
    ```
10. **Run Celery worker:**
    ```
    celery -A image_processing_service worker -l info
    ```
11. **Run Celery beat (for scheduled tasks):**
    ```
    celery -A image_processing_service beat -l info
    ```

## Environment Variables (`.env`)

You'll need to set the following environment variables in your `.env` file.  **Do not commit your `.env` file to version control.**

```
SECRET_KEY=your_django_secret_key
DEBUG=True  # Set to False in production
DATABASE_URL=postgres://user:password@host:port/database_name
CELERY_BROKER_URL=redis://localhost:6379/0  # Or your Redis URL
CELERY_RESULT_BACKEND=redis://localhost:6379/0 # Or your Redis URL
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_STORAGE_BUCKET_NAME=your_s3_bucket_name
AWS_S3_REGION_NAME=your_s3_region  # e.g., us-east-1
MEDIA_ROOT=media #your media root
MEDIA_URL=/media/ #your media url
MAX_IMAGE_SIZE=10485760 #your max image size, example: 10MB
SENTRY_DSN=your_sentry_dsn # sentry
# Add other environment variables as needed (e.g., for email settings, API keys)
```

## API Documentation

[To be added: Link to API documentation (e.g., Swagger UI, Postman collection).]

## Deployment

[To be added: Instructions for deploying the application (e.g., to AWS, Heroku, etc.).]

## Contributing

[To be added: Guidelines for contributing to the project (e.g., how to submit pull requests).]

## License

[To be added: Choose a license for your project (e.g., MIT, Apache 2.0).]
