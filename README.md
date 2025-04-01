# Image Processing Service API

This repository contains the backend for an image processing service, built with Django and Django REST Framework (DRF). It allows users to upload images, perform various transformations, and retrieve images in different formats.

## Project Structure

The project is structured as follows:

```
image-processing-service-api/   # Project root directory
├── api/                        # Django app for the API (views, serializers, models, etc.)
├── compose/                    # Docker Compose configurations (local, production, etc.)
│   ├── local/
│   │   ├── django/
│   │   ├── worker/
│   │   └── ...
│   └── ...
├── elk/                        # ELK stack configurations (Elasticsearch, Logstash, Kibana)
│   ├── local/
│   │   ├── elasticsearch/
│   │   ├── filebeat/
│   │   └── kibana/
├── image_processing_service/   # Django project settings directory (settings.py, urls.py, etc.)
├── image_processor/            # Django app for image processing logic (tasks, models, etc.)
├── logs/                       # Log files directory (mounted in Docker)
├── posting-collection/         # (Optional) Postman collection or similar API testing files
├── utils/                      # Shared utility functions and custom exceptions
├── .dockerignore               # Specifies files/directories Docker should ignore
├── .env.example                # Example environment variables file
├── .gitignore                  # Files and directories to ignore in Git
├── docker-compose.local.yml    # Docker Compose file for local development
├── justfile                    # Just command runner configuration
├── LICENSE                     # Project license file (MIT)
├── manage.py                   # Django management script
├── README.md                   # This file
└── requirements.txt            # Project dependencies
```

*   **`api/`:** Handles API requests/responses, authentication, serialization, and API-specific models.
*   **`compose/`:** Contains Docker Compose files for different environments (e.g., `local`).
*   **`elk/`:** Contains configuration files for the ELK stack used for logging.
*   **`image_processing_service/`:** Contains the main Django project settings, URL configurations, and ASGI/WSGI entry points.
*   **`image_processor/`:** Contains the core image processing logic, including Celery tasks and related models.
*   **`utils/`:** Contains shared helper functions and custom exception classes used across the project.

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
    *   Uses Redis for caching API responses and potentially transformed image data.
*   **Rate Limiting:**
    *   Implements rate limiting (per user/anonymous) using Django REST Framework.
* **Error Handling:**
    * Provides appropriate HTTP status and error responses.
* **Logging:**
    * Uses the ELK stack (Elasticsearch, Kibana, Filebeat) via Docker for centralized logging.

## Technologies Used

*   **Python:** Programming language.
*   **Django:** Web framework.
*   **Django REST Framework (DRF):**  Toolkit for building Web APIs.
*   **Celery:** Distributed task queue for asynchronous processing.
*   **Pillow:** Image processing library.
*   **PostgreSQL:** Database.
*   **Amazon S3:** Object storage for images.
*   **Redis:** In-memory data store (for caching and Celery broker/backend).
*   **JWT:** JSON web token for authentication.
*   **Sentry:** For error tracking.
*   **ELK Stack (Elasticsearch, Kibana, Filebeat):** For centralized logging and monitoring.
*   **Docker & Docker Compose:** For containerization and local development environment setup.
*   **Just:** Command runner for simplifying common development tasks (like Docker management).

## Setup (Local Development with Docker)

This project uses Docker and Docker Compose for a consistent local development environment. It also utilizes `just` for simplified command execution.

**Prerequisites:**

*   **Docker:** Install Docker Desktop or Docker Engine.
*   **Just:** Install the `just` command runner (see [https://github.com/casey/just](https://github.com/casey/just)).

**Steps:**

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd image-processing-service-api
    ```

2.  **Set up environment variables:**
    *   Copy the example environment file:
        ```bash
        cp .env.example .env
        ```
    *   Edit the `.env` file in the project root and fill in the required values (see the Environment Variables section below). **Crucially, set your AWS credentials and S3 bucket details.**

3.  **Build and start the services:**
    *   Use the `just` command to build the Docker images and start all services (Django, DB, Redis, Worker, ELK):
        ```bash
        just build
        just up
        ```
    *   Alternatively, use Docker Compose directly:
        ```bash
        docker compose build
        docker compose up -d --remove-orphans
        ```

4.  **Run database migrations:**
    *   Once the containers are running, execute migrations inside the Django container:
        ```bash
        docker compose exec django python manage.py makemigrations
        docker compose exec django python manage.py migrate
        ```

5.  **Access the services:**
    *   **API:** `http://localhost:8000`
    *   **Kibana (Logs):** `http://localhost:5601`
    *   **Django Debugger (if enabled):** Port `5678`
    *   **Celery Worker Debugger (if enabled):** Port `5679`

**Common `just` Commands:**

*   `just up`: Start all services defined in `docker-compose.local.yml`.
*   `just down`: Stop all running services.
*   `just logs django`: Tail the logs for the Django service (replace `django` with `worker`, `db`, etc. as needed).
*   `just prune`: Stop services and remove associated volumes (use with caution!).
*   `just up_services`: Start supporting services (DB, Redis, ELK, Worker) without starting the main Django app container (useful if you want to run Django locally outside Docker but use the containerized services).

## Environment Variables (`.env`)

You'll need to set the following environment variables in your `.env` file.  **Do not commit your `.env` file to version control.**

```dotenv
# Django Core
DJANGO_SECRET_KEY=your_strong_random_secret_key
DEBUG=True # Set to False in production

# Database (PostgreSQL - used by docker-compose.local.yml)
DB_NAME=image_processing_db
DB_USER=image_processing_user
DB_PASSWORD=your_db_password
DB_HOST=db # Service name in docker-compose
DB_PORT=5432

# Celery (using Redis broker)
CELERY_BROKER_URL=redis://@redis:6379/0 # Service name in docker-compose

# Cache (using Redis)
CACHE_REDIS_URL=redis://@redis:6379/1 # Use a different DB number for cache

# AWS S3 Storage
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_STORAGE_BUCKET_NAME=your_s3_bucket_name
AWS_S3_REGION_NAME=your_s3_region # e.g., us-east-1

# Sentry (Optional Error Tracking)
SENTRY_DSN=your_sentry_dsn

# Logging (File path used by Filebeat in Docker)
LOG_FILE_PATH=/var/log/django/django.log

# JWT Settings (Optional overrides)
# ACCESS_TOKEN_LIFETIME=5
# REFRESH_TOKEN_LIFETIME=60

# Image Validation (Optional overrides)
# IMAGE_MAX_PIXEL_SIZE=4096
# IMAGE_MIN_PIXEL_SIZE=100

# Debugging (Optional - Port used by docker-compose.local.yml)
# REMOTE_DEBUGGING_PORT=5678
```

## API Documentation

[To be added: Link to API documentation (e.g., Swagger UI, Postman collection).]

## Deployment

[To be added: Instructions for deploying the application (e.g., to AWS, Heroku, etc.).]

## Contributing

[To be added: Guidelines for contributing to the project (e.g., how to submit pull requests).]

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
