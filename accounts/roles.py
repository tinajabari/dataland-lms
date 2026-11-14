"""
منطق نقش‌ها و سطح دسترسی (Role-Based Access Control).

نقش‌ها:
    admin       مدیر    - دسترسی کامل (مدیریت کاربران، همه دوره‌ها)
    instructor  مدرس    - مدیریت دوره‌ها/درس‌های خودش و دیدن دانشجوهای آن‌ها
    student     دانشجو  - ثبت‌نام در دوره‌ها و دیدن محتوای دوره‌های خودش
"""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import Profile

ADMIN = Profile.ADMIN
INSTRUCTOR = Profile.INSTRUCTOR
STUDENT = Profile.STUDENT


def _default_role_for(user):
    """نقش پیش‌فرض برای کاربرانی که هنوز پروفایل ندارند (مثلاً قبل از LMS ساخته شدن)."""
    if user.is_superuser:
        return ADMIN
    if hasattr(user, 'instructor_profile'):
        return INSTRUCTOR
    return STUDENT


def get_profile(user):
    """پروفایل کاربر را برمی‌گرداند (اگر نبود می‌سازد)."""
    if not getattr(user, 'is_authenticated', False):
        return None
    try:
        return user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=user, role=_default_role_for(user))
        user.profile = profile
        return profile


def get_role(user):
    """نقش کاربر: 'admin' / 'instructor' / 'student' (برای کاربر لاگین‌نکرده None)."""
    profile = get_profile(user)
    if profile is None:
        return None
    if user.is_superuser:
        return ADMIN
    return profile.role


def is_admin(user):
    return get_role(user) == ADMIN


def is_instructor(user):
    return get_role(user) == INSTRUCTOR


def is_student(user):
    return get_role(user) == STUDENT


def set_role(user, role):
    """
    نقش کاربر را تغییر می‌دهد و پروفایل‌های وابسته (مدرس/دانشجو) را می‌سازد.
    - مدیر: دسترسی ادمین جنگو هم می‌گیرد (is_staff / is_superuser)
    - مدرس/دانشجو: دسترسی ادمین جنگو برداشته می‌شود
    توجه: پروفایل مدرس هیچ‌وقت حذف نمی‌شود تا دوره‌های او از بین نرود.
    """
    from courses.models import Instructor, Student  # import محلی برای جلوگیری از چرخه

    if role not in (ADMIN, INSTRUCTOR, STUDENT):
        raise ValueError(f'نقش نامعتبر: {role}')

    profile = get_profile(user)
    profile.role = role
    profile.save(update_fields=['role'])

    user.is_staff = role == ADMIN
    user.is_superuser = role == ADMIN
    user.save(update_fields=['is_staff', 'is_superuser'])

    if role == INSTRUCTOR:
        Instructor.objects.get_or_create(user=user)
    elif role == STUDENT:
        Student.objects.get_or_create(user=user)
    return profile


def role_required(*roles):
    """
    دکوراتور دسترسی: فقط کاربرانی با یکی از نقش‌های داده‌شده اجازه ورود دارند.
    کاربر لاگین‌نکرده به صفحه ورود هدایت می‌شود؛ کاربر بدون دسترسی خطای ۴۰۳ می‌گیرد.
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if get_role(request.user) not in roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def can_manage_course(user, course):
    """مدیر همه دوره‌ها را می‌تواند مدیریت کند؛ مدرس فقط دوره‌های خودش را."""
    role = get_role(user)
    if role == ADMIN:
        return True
    if role == INSTRUCTOR:
        return course.instructor.user_id == user.id
    return False


def deny_with_message(request, text='شما اجازه‌ی انجام این کار را ندارید.'):
    messages.error(request, text)
