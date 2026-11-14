from .roles import get_role, ADMIN, INSTRUCTOR, STUDENT


def roles(request):
    """نقش کاربر را برای همه قالب‌ها در دسترس می‌کند (user_role, is_admin, ...)."""
    user = getattr(request, 'user', None)
    role = get_role(user) if user is not None and user.is_authenticated else None
    return {
        'user_role': role,
        'is_admin': role == ADMIN,
        'is_instructor': role == INSTRUCTOR,
        'is_student': role == STUDENT,
    }
