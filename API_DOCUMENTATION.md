# API Documentation

This document provides examples of requests and responses for the API endpoints.

## Authentication

All authentication endpoints are prefixed with `/api/auth/`.

---

### Login

Authenticates a user and returns an access and refresh token.

**Request:**
```http
POST /api/auth/login/
Content-Type: application/json

{
    "username": "string",
    "password": "string"
}
```

**Response:**
```json
{
    "access_token": "string",
    "refresh_token": "string",
    "user": {
        "pk": 0,
        "username": "string",
        "email": "user@example.com",
        "first_name": "string",
        "last_name": "string"
    }
}
```

---

### Logout

Logs out the current user.

**Request:**
```http
POST /api/auth/logout/
```
*(Requires authentication)*

**Response:**
```json
{
    "detail": "Successfully logged out."
}
```

---

### Register

Registers a new user.

**Request:**
```http
POST /api/auth/registration/
Content-Type: application/json

{
    "username": "string",
    "email": "user@example.com",
    "password": "string",
    "password2": "string"
}
```

**Response:**
```json
{
    "access_token": "string",
    "refresh_token": "string",
    "user": {
        "pk": 0,
        "username": "string",
        "email": "user@example.com",
        "first_name": "string",
        "last_name": "string"
    }
}
```

---

### Password Reset

Initiates the password reset process.

**Request:**
```http
POST /api/auth/password/reset/
Content-Type: application/json

{
    "email": "user@example.com"
}
```

**Response:**
```json
{
    "detail": "Password reset e-mail has been sent."
}
```

---

### Password Reset Confirm

Confirms the password reset with a new password.

**Request:**
```http
POST /api/auth/password/reset/confirm/
Content-Type: application/json

{
    "new_password1": "string",
    "new_password2": "string",
    "uid": "string",
    "token": "string"
}
```

**Response:**
```json
{
    "detail": "Password has been reset with the new password."
}
```

---

### Password Change

Changes the password for the authenticated user.

**Request:**
```http
POST /api/auth/password/change/
Content-Type: application/json

{
    "new_password1": "string",
    "new_password2": "string"
}
```
*(Requires authentication)*

**Response:**
```json
{
    "detail": "New password has been saved."
}
```

---

### Get User Details

Retrieves details for the authenticated user.

**Request:**
```http
GET /api/auth/user/
```
*(Requires authentication)*

**Response:**
```json
{
    "pk": 0,
    "username": "string",
    "email": "user@example.com",
    "first_name": "string",
    "last_name": "string"
}
```

---

### Update User Details

Updates details for the authenticated user.

**Request:**
```http
PUT /api/auth/user/
Content-Type: application/json

{
    "username": "string",
    "email": "user@example.com",
    "first_name": "string",
    "last_name": "string"
}
```
*(Requires authentication)*

**Response:**
```json
{
    "pk": 0,
    "username": "string",
    "email": "user@example.com",
    "first_name": "string",
    "last_name": "string"
}
```

---

### Partially Update User Details

Partially updates details for the authenticated user.

**Request:**
```http
PATCH /api/auth/user/
Content-Type: application/json

{
    "first_name": "string"
}
```
*(Requires authentication)*

**Response:**
```json
{
    "pk": 0,
    "username": "string",
    "email": "user@example.com",
    "first_name": "string",
    "last_name": "string"
}
```

---

### Token Verification

Verifies a JWT token.

**Request:**
```http
POST /api/token/verify/
Content-Type: application/json

{
    "token": "string"
}
```

**Response:**
```json
{}
```

---

### Token Refresh

Refreshes an access token using a refresh token.

**Request:**
```http
POST /api/token/refresh/
Content-Type: application/json

{
    "refresh": "string"
}
```

**Response:**
```json
{
    "access": "string"
}
```

## Image Management

---

### List Source Images

Lists all source images owned by the user.

**Request:**
```http
GET /api/images/
```
*(Requires authentication)*

**Response:**
```json
[
    {
        "id": 0,
        "file_name": "string",
        "description": "string",
        "file": "string (url)",
        "owner": 0
    }
]
```

---

### Retrieve Source Image

Retrieves a specific source image by its ID.

**Request:**
```http
GET /api/images/<id>/
```
*(Requires authentication)*

**Response:**
```json
{
    "id": 0,
    "file_name": "string",
    "description": "string",
    "file": "string (url)",
    "owner": 0,
    "metadata": {},
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z"
}
```

---

### Upload Image

Uploads a new image. This is a `multipart/form-data` request.

**Request:**
```http
POST /api/images/upload/
Content-Type: multipart/form-data

{
    "file": "<image_file>",
    "description": "string"
}
```
*(Requires authentication)*

**Response:**
```json
{
    "id": 0,
    "file": "string (url)",
    "file_name": "string",
    "description": "string"
}
```

---

### List Transformed Images

Lists all transformed images owned by the user.

**Request:**
```http
GET /api/images/transformed/
```
*(Requires authentication)*

**Response:**
```json
[
    {
        "id": 0,
        "file_name": "string",
        "description": "string",
        "file": "string (url)",
        "owner": 0
    }
]
```

---

### Retrieve Transformed Image

Retrieves a specific transformed image by its ID.

**Request:**
```http
GET /api/images/transformed/<id>/
```
*(Requires authentication)*

**Response:**
```json
{
    "id": 0,
    "file_name": "string",
    "description": "string",
    "file": "string (url)",
    "owner": 0,
    "metadata": {},
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z",
    "source_image": 0,
    "transformation_task": 0
}
```

## Image Transformation

---

### Create Transformation Task

Creates a new task to transform an image.

**Request:**
```http
POST /api/images/<id>/transform/
Content-Type: application/json

{
    "transformations": {
        "resize": {
            "width": 100,
            "height": 100
        },
        "rotate": 90
    },
    "format": "JPEG"
}
```
*(Requires authentication)*

**Response:**
```json
{
    "id": 0,
    "original_image": 0,
    "result_image": null,
    "status": "PENDING",
    "transformations": {
        "resize": {
            "width": 100,
            "height": 100
        },
        "rotate": 90
    },
    "format": "JPEG",
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z",
    "error_message": null
}
```

---

### List Transformation Tasks

Lists all transformation tasks for the user.

**Request:**
```http
GET /api/tasks/
```
*(Requires authentication)*

**Response:**
```json
[
    {
        "id": 0,
        "original_image": 0,
        "result_image": 0,
        "status": "string",
        "transformations": {},
        "format": "string",
        "created_at": "2024-01-01T12:00:00Z",
        "updated_at": "2024-01-01T12:00:00Z",
        "error_message": "string"
    }
]
```

---

### Retrieve Transformation Task

Retrieves a specific transformation task by its ID.

**Request:**
```http
GET /api/tasks/<id>/
```
*(Requires authentication)*

**Response:**
```json
{
    "id": 0,
    "original_image": 0,
    "result_image": 0,
    "status": "string",
    "transformations": {},
    "format": "string",
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z",
    "error_message": "string"
}
``` 