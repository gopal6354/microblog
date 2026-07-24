from models.user import RoleChoice
from models.user import User


def is_super_admin(exist_user):
    return exist_user.role == RoleChoice.SUPER_ADMIN


def is_user_soft_deleted(user: User):
    return user.is_deleted
