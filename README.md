# EchoHub

EchoHub is a FastAPI-based web application built to learn modern backend development. The project currently includes user authentication, email OTP verification, password reset, profile management, and server-side rendered pages using Jinja2 templates.

## Features

### User Features

- **User Registration** – Create a new account.
- **Email OTP Verification** – Verify the account using a one-time password (OTP) sent to the registered email.
- **Login** – Sign in using an email address or username with JWT authentication stored in an HTTP-only cookie.
- **Forgot Password** – Request an OTP via email to reset the account password.
- **Reset Password** – Set a new password after successful OTP verification.
- **Logout** – Securely log out by removing the authentication cookie.
- **Profile Management** – Update profile information, including profile picture, username, bio, and other details.
- **Blog Management** – Create, edit, update, and delete personal blog posts.
- **Blog Feed** – Browse all blog posts displayed in reverse chronological order (newest first).
- **Likes** – Like or unlike blog posts with an automatically updated like count.
- **Report Blogs** – Report inappropriate blog posts (excluding your own posts).
- **Account Reactivation** – Submit a request to reactivate a deactivated account.

---

### Admin Features

- **Initial Admin Setup** – Create the first administrator account using a seed script.
- **Shared Authentication** – Use the same authentication flow as regular users, including login, OTP verification, password reset, and logout.
- **Role-Based Access Control (RBAC)** – Restrict administrative features based on user roles.
- **User Management** – View, soft delete, and permanently delete user accounts.
- **Blog Management** – View, soft delete, and permanently delete blog posts.
- **Report Management** – Review reported blog posts and take appropriate moderation actions.
- **Account Activation Management** – Approve or reject user account activation requests.

## Tech Stack

### Backend
- Python 3.14
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
- JWT (JSON Web Token)
- HTTP-only Cookies
- Passlib
- Bcrypt

### Email Service
- SMTP (Email OTP Verification)

### Development Tools
- Uvicorn
- Git
- GitHub


## Project Structure

```text
app/
├── admin_panel/
│   ├── routes/                  # Admin routes
│   └── services/                # Admin business logic
│
├── alembic/                     # Database migrations
│   └── versions/
│
├── auth/
│   ├── routers/                 # Authentication routes
│   └── services/                # Authentication business logic
│
├── core/
│   ├── config.py                # Application configuration
│   ├── middleware.py            # Custom middleware
│   └── exceptions.py            # Exception handlers
│
├── dependencies/                # Shared dependencies
│   └── auth.py
│
├── echohub/
│   └── routers/
│       ├── echohub.py           # Home routes
│       └── blog.py              # Blog routes
│
├── models/                      # SQLAlchemy models
│   ├── user.py
│   ├── blogs.py
│   ├── like.py
│   ├── report.py
│   └── activation_request.py
│
├── schemas/                     # Pydantic schemas
│
├── scripts/                     # Utility scripts
│   └── create_super_admin.py
│
├── static/
│   ├── admin/                   # Admin assets
│   ├── user/                    # User assets
│   └── uploads/                 # Uploaded images and videos
│
├── templates/
│   ├── admin/
│   ├── auth/
│   ├── blog/
│   ├── partials/
│   └── user/
│
├── user/
│   └── routers/                 # User routes
│
├── utils/                       # Helper utilities
│   ├── email_service.py
│   ├── file_upload.py
│   ├── flash.py
│   ├── otp.py
│   ├── otp_service.py
│   └── security.py
│
├── database.py                  # Database connection
├── main.py                      # FastAPI application entry point
├── requirements.txt
└── README.md




## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/gopal6354/microblog.git
```

### 2. Navigate to the Project Directory

```bash
cd echohub
```

### 3. Create a Virtual Environment

```bash
python -m venv venv
```

### 4. Activate the Virtual Environment

**Linux/macOS**

```bash
source venv/bin/activate
```

**Windows**

```bash
venv\Scripts\activate
```

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```
```

## Database Setup

Run the Alembic migrations to create the database tables.

```bash
alembic upgrade head

## Running the Application

Start the FastAPI development server:

```bash
uvicorn main:app --reload
```

The application will be available at:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

Alternative API documentation:

```text
http://127.0.0.1:8000/redoc
```
```
