from .models import UserProfile
from .role_utils import get_active_user_role


def build_user_auth_payload(user):
    role, role_code = get_active_user_role(user)
    profile, _ = UserProfile.objects.get_or_create(user=user)

    display_role = role.name if role else ("Admin" if role_code == "ADMIN" else "")
    if user.is_superuser and not display_role:
        display_role = "Admin"

    display_name = user.get_full_name().strip() or user.username

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email or "",
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "is_superuser": user.is_superuser,
        "role": display_role,
        "role_code": role_code or "",
        "display_name": display_name,
        "emp_code": profile.emp_code,
        "designation": profile.designation,
        "department": profile.department,
        "mobile_no": profile.mobile_no,
    }
