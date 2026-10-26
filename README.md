# EchoHub

EchoHub is a FastAPI-based blogging and community platform designed for learning backend development with modern Python patterns. The application includes user authentication, account verification, profile management, blog publishing, likes, reporting, admin moderation, and account reactivation workflows.

## Features

### User Features

- User registration with validation and email verification
- OTP-based email verification
- Login with email or username using JWT stored in an HTTP-only cookie
- Password reset flow using OTP verification
- Secure logout
- Profile management including username, bio, and profile image updates
- Blog creation, editing, and deletion
- Blog feed with reverse chronological ordering
- Like and unlike functionality with live counts
- Report inappropriate blog posts
- Account reactivation request flow for inactive or soft-deleted users

### Admin Features

- Initial admin setup via a seed script
- Role-based access control
- User management: view, soft delete, and permanent delete
- Blog moderation: view, soft delete, and permanent delete
- Report review and moderation tools
- Approval and rejection of account activation requests

## Tech Stack

### Backend
- Python 3.12+
- FastAPI
- SQLAlchemy 2.0
- Alembic
- PostgreSQL

### Frontend
- HTML5
- CSS3
- Bootstrap 5
- Jinja2 Templates

### Authentication & Security
- JWT
- HTTP-only cookies
- Passlib
- Bcrypt
- Pydantic settings

### Email / Notifications
- SMTP-based email OTP flow
- Sentry error tracking

### Development Tools
- Uvicorn
- Docker / Docker Compose
- PostgreSQL
- Git / GitHub

## Project Structure

```text
.
├── .github/
├── app/
│   ├── admin_panel/
│   │   ├── routes/
│   │   └── services/
│   ├── alembic/
│   │   └── versions/
│   ├── auth/
│   │   ├── routers/
│   │   └── services/
│   ├── core/
│   │   ├── config.py
│   │   ├── middleware.py
│   │   └── exceptions.py
│   ├── dependencies/
│   │   └── auth.py
│   ├── echohub/
│   │   └── routers/
│   │       ├── echohub.py
│   │       └── blog.py
│   ├── models/
│   │   ├── user.py
│   │   ├── blogs.py
│   │   ├── like.py
│   │   ├── report.py
│   │   └── activation_request.py
│   ├── schemas/
│   ├── scripts/
│   │   └── create_super_admin.py
│   ├── static/
│   │   ├── admin/
│   │   ├── user/
│   │   └── uploads/
│   ├── templates/
│   │   ├── admin/
│   │   ├── auth/
│   │   ├── blog/
│   │   ├── partials/
│   │   └── user/
│   ├── test/
│   ├── user/
│   │   └── routers/
│   ├── utils/
│   │   ├── email_service.py
│   │   ├── file_upload.py
│   │   ├── flash.py
│   │   ├── otp.py
│   │   ├── otp_service.py
│   │   └── security.py
│   ├── .dockerignore
│   ├── .env.example
│   ├── .gitignore
│   ├── alembic.ini
│   ├── compose.yaml
│   ├── database.py
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── .pre-commit-config.yaml
├── README.md
└── LICENSE (if present in your repository)
```

## Prerequisites

Before running the project, make sure you have:

- Python 3.12 or newer
- PostgreSQL running locally or a Docker-based PostgreSQL instance
- Docker and Docker Compose (optional, for containerized setup)
- An SMTP email provider or mail server for OTP delivery

## Environment Setup

Navigate to the application folder and create a `.env` file based on `.env.example`.

```bash
cd app
cp .env.example .env
```

Update `.env` with your own settings:

```dotenv
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_TIME=7
REFRESH_TOKEN_EXPIRE_TIME=30
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/echohub
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_ADDRESS=your_email@example.com
EMAIL_PASSWORD=your_email_password
SENTRY_DSN=
SENTRY_ENVIRONMENT=development
```

If you are using Docker Compose, configure PostgreSQL variables in `.env` as well:

```dotenv
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=echohub
```

## Installation

### Option 1: Local Development

```bash
cd app
python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
# venv\Scripts\activate

pip install -r requirements.txt
```

### Option 2: Docker Compose

From the `app` directory:

```bash
cd app
docker compose up --build
```

This will start:
- the FastAPI app on port `9000`
- PostgreSQL on the default Compose network

## Database Setup

Run migrations inside the app directory:

```bash
cd app
alembic upgrade head
```

## Running the Application

### Local

```bash
cd app
uvicorn main:app --reload
```

Application URL:

```text
http://127.0.0.1:8000
```

Swagger docs:

```text
http://127.0.0.1:8000/docs
```

Redoc docs:

```text
http://127.0.0.1:8000/redoc
```

## Docker Notes

The project includes a `Dockerfile` and `compose.yaml` for quick local setup.

```bash
cd app
docker build -t echohub .
docker run -p 8000:8000 --env-file .env echohub
```

## Admin Setup

To create the initial admin account, use the seed script inside the app folder.

```bash
cd app
python scripts/create_super_admin.py
```

Follow the script instructions to create the first super admin user.

## Notes

- The app is structured around a modular FastAPI design with routers, services, models, and templates.
- Authentication and password reset flows use OTP-based email verification.
- The app is intended for learning and project experimentation, but the core workflows are production-oriented in structure.

## License

This project does not currently declare a license in the repository root. Add a license file if you want to specify usage terms.

## Contributing

Contributions are welcome. If you want to improve the project, fork the repository, create a feature branch, and open a pull request.

```bash
git checkout -b feature/my-change
git commit -am "Add my change"
git push origin feature/my-change
```
