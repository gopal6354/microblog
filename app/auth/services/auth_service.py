from models.user import RoleChoice
from models.user import User
from sqlalchemy import select, or_


def is_super_admin(exist_user):
    return exist_user.role == RoleChoice.SUPER_ADMIN


def is_user_soft_deleted(user: User):
    return user.is_deleted


def is_user_exist(user, session):
    return session.scalar(
        select(User).where(
            or_(User.email == user.email, User.username == user.username)
        )
    )
