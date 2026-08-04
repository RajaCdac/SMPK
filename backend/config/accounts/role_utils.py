from .models import UserRole
from .role_codes import ADMIN_ROLE_CODES, normalize_role_code, role_name_to_code


def get_active_user_role(user):
    if not user or not getattr(user, "is_authenticated", False):
        return None, None

    if getattr(user, "is_superuser", False):
        assignment = (
            UserRole.objects.filter(
                user=user,
                is_active=True,
                role__is_active=True,
            )
            .select_related("role")
            .order_by("id")
            .first()
        )
        if assignment:
            role = assignment.role
            code = normalize_role_code(role.code, role.name)
            return role, code
        return None, "ADMIN"

    assignment = (
        UserRole.objects.filter(
            user=user,
            is_active=True,
            role__is_active=True,
        )
        .select_related("role")
        .order_by("id")
        .first()
    )
    if not assignment:
        return None, None

    role = assignment.role
    code = normalize_role_code(role.code, role.name)
    return role, code


def user_is_admin(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    _, code = get_active_user_role(user)
    return code == "ADMIN"


def user_is_pension_user(user):
    if not user or not user.is_authenticated:
        return False
    _, code = get_active_user_role(user)
    if code == "ADMIN":
        return False
    return code is not None
