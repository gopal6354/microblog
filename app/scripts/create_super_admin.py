
import argparse
import os
from getpass import getpass

from database import Session
from models.user import User, RoleChoice, StatusChoice
from utils.security import hash_password


def create_super_admin(from_env=False):
    db = Session()

    try:
        existing_admin = (
            db.query(User)
            .filter(User.role == RoleChoice.SUPER_ADMIN)
            .first()
        )

        if existing_admin:
            print("Super Admin already exists")
            return

        if from_env:
            username = os.getenv("INITIAL_ADMIN_USERNAME", "").strip()
            email = os.getenv("INITIAL_ADMIN_EMAIL", "").strip()
            password = os.getenv("INITIAL_ADMIN_PASSWORD", "")

            if not username or not email or not password:
                raise RuntimeError(
                    "Missing initial admin credentials in environment"
                )
        else:
            username = input("Enter username: ").strip()
            email = input("Enter email: ").strip()
            password = getpass("Enter password: ")
            confirm_password = getpass("Enter confirm password: ")

            if not username or not email or not password:
                print("All fields are required")
                return

            if password != confirm_password:
                print("Password and confirm password do not match")
                return

        existing_user = (
            db.query(User)
            .filter(
                (User.username == username)
                | (User.email == email)
            )
            .first()
        )

        if existing_user:
            if from_env:
                raise RuntimeError(
                    "Username or email already exists; "
                    "choose unused credentials"
                )

            print("Username or email already exists")
            return

        admin = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            role=RoleChoice.SUPER_ADMIN,
            status=StatusChoice.ACTIVE,
            otp_verified=True,
        )

        db.add(admin)
        db.commit()

        print("Super Admin created successfully")

    except Exception:
        db.rollback()

        if from_env:
            raise

        print("Error creating Super Admin")

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--from-env",
        action="store_true",
        help="Read initial admin credentials from environment variables",
    )
    args = parser.parse_args()

    create_super_admin(from_env=args.from_env)
