from models.user import RoleChoice


def is_super_admin(exist_user):
    return exist_user.role == RoleChoice.SUPER_ADMIN
