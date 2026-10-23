from database import Session
from models.user import User, RoleChoice, StatusChoice
from utils.security import hash_password
from getpass import getpass


def create_super_admin():
    db = Session()

    try:
        existing_admin = (
            db.query(User).filter(User.role == RoleChoice.SUPER_ADMIN).first()
        )

        if existing_admin:
            print("Super Admin already exists")
            return

        username = input("Enter username: ")
        email = input("Enter email: ")
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
            .filter((User.username == username) | (User.email == email))
            .first()
        )

        if existing_user:
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

    except Exception as e:
        db.rollback()
        print("Error:", e)

    finally:
        db.close()


if __name__ == "__main__":
    create_super_admin()
