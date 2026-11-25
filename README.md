# EchoHub

EchoHub is a server-rendered social microblog built with FastAPI, SQLAlchemy, PostgreSQL, Jinja2, and Bootstrap. It supports account verification, posts with image and video attachments, social interactions, discovery, notifications, and role-based moderation.

## Features

### Accounts

- Registration and login with username or email
- Email OTP verification and resend
- Password reset by OTP
- HTTP-only JWT access and refresh cookies
- Profile editing and profile pictures
- Account activation requests
- Password and privacy settings
- Blocked and muted users

### Posts and Social Features

- Create, edit, publish, and delete blog posts
- Image and video attachments
- Draft and published post states
- Post location
- Chronological home feed and trending tags
- Likes, comments, reposts, bookmarks, and reports
- Follow users and private follow requests
- Public profile pages and relation lists
- Search and tag-based discovery

### Notifications and Moderation

- Notifications for social activity
- Super-admin dashboard
- Lock, restore, and permanently delete users
- Hide, restore, and permanently delete posts
- Review reports and update their moderation status
- Approve or reject account activation requests

## Tech Stack

- **Backend:** Python 3.12+, FastAPI
- **Database:** SQLAlchemy 2.0, Alembic, PostgreSQL
- **Templates:** Jinja2
- **Frontend:** HTML5, CSS3, Bootstrap 5, JavaScript
- **Authentication:** python-jose JWT, Passlib/Bcrypt
- **Email:** SMTP
- **Observability:** Sentry
- **Media:** Local static uploads or Cloudinary
- **Testing:** pytest
- **Deployment:** Docker and Docker Compose

## Project Structure

```text
.
├── app/
│   ├── admin_panel/       # Admin routes and moderation services
│   ├── auth/              # Registration, login, OTP, and password reset
│   ├── alembic/           # Database migrations
│   ├── core/              # Settings, middleware, and exceptions
│   ├── dependencies/      # FastAPI dependencies
│   ├── echohub/           # Feed, posts, social features, discovery, and notifications
│   ├── models/            # SQLAlchemy models
│   ├── schemas/           # Pydantic schemas
│   ├── scripts/           # Administrative utility scripts
│   ├── static/            # CSS, JavaScript, and uploaded media
│   ├── templates/         # Jinja2 templates
│   ├── test/              # pytest test suite
│   ├── user/              # Profiles, settings, and social relations
│   └── utils/             # Email, uploads, security, pagination, and helpers
├── .github/workflows/     # CI and container build workflow
└── README.md
```

## Prerequisites

- Python 3.12 or newer
- PostgreSQL 17 (or Docker and Docker Compose)
- An SMTP account for OTP and notification emails

## Local Setup

### 1. Clone and enter the repository

```bash
git clone https://github.com/gopal6354/microblog.git
cd microblog
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

On Windows:

```powershell
py -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r app/requirements.txt
```

### 4. Configure environment variables

Create `app/.env` using the provided example:

```bash
cp app/.env.example app/.env
```

Set all required values before starting the application.

| Variable | Description |
|---|---|
| `SECRET_KEY` | Secret used for sessions and JWT signing |
| `ALGORITHM` | JWT signing algorithm, normally `HS256` |
| `ACCESS_TOKEN_EXPIRE_TIME` | Access-token lifetime in days |
| `REFRESH_TOKEN_EXPIRE_TIME` | Refresh-token lifetime in days |
| `DATABASE_URL` | SQLAlchemy database URL |
| `EMAIL_HOST` | SMTP server hostname |
| `EMAIL_PORT` | SMTP server port |
| `EMAIL_ADDRESS` | Sender email address |
| `EMAIL_PASSWORD` | SMTP password or app password |
| `SENTRY_DSN` | Sentry DSN, or an empty string when unused |
| `SENTRY_ENVIRONMENT` | Sentry environment name |
| `COOKIE_SECURE` | Set `true` to require HTTPS auth cookies |
| `USE_CLOUDINARY` | Set `true` for Cloudinary media uploads |
| `CLOUDINARY_URL` | Cloudinary URL when `USE_CLOUDINARY=true` |

Example local PostgreSQL URL:

```text
postgresql://microblog:microblog@127.0.0.1:5432/microblog
```

### 5. Apply database migrations

Run this from the `app` directory:

```bash
cd app
alembic upgrade head
```

### 6. Create a super administrator

The first super administrator is created interactively:

```bash
python -m scripts.create_super_admin
```

### 7. Start the development server

```bash
uvicorn main:app --reload
```

Open:

- Application: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## Docker Compose

Copy the environment example and provide the database and application values:

```bash
cp app/.env.example app/.env
docker compose -f app/compose.yaml up --build
```

The Compose setup starts PostgreSQL 17 and the FastAPI container. EchoHub is available at:

- http://localhost:9000
- http://localhost:9000/docs

The container runs `alembic upgrade head` before starting Uvicorn. Uploaded files are stored in `app/static/uploads` unless Cloudinary is enabled.

Stop the containers with:

```bash
docker compose -f app/compose.yaml down
```

Use `docker compose -f app/compose.yaml down -v` to also remove the PostgreSQL data volume.

## Running Tests

Tests use an isolated temporary SQLite database and do not require PostgreSQL or a real SMTP server.

```bash
cd app
pytest
```

The test suite covers authentication, posts, social features, notifications, pagination, and admin-facing behavior.

## Media Uploads

Local uploads support:

- Images: `.jpg`, `.jpeg`, `.jfif`, `.png`, `.gif`, `.webp` up to 10 MB
- Videos: `.mp4`, `.mov`, `.webm` up to 50 MB

Set `USE_CLOUDINARY=true` and provide `CLOUDINARY_URL` to store uploads in Cloudinary instead.
