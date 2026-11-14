from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile_for_new_user(sender, instance, created, raw=False, **kwargs):
    """برای هر کاربر جدید (از هر راهی ساخته شود) یک پروفایل نقش می‌سازد."""
    if created and not raw:
        Profile.objects.get_or_create(
            user=instance,
            defaults={'role': Profile.ADMIN if instance.is_superuser else Profile.STUDENT},
        )


def sync_role_for_new_instructor(sender, instance, created, raw=False, **kwargs):
    """
    وقتی مدیر از پنل ادمین یک «استاد» برای کاربری می‌سازد،
    نقش آن کاربر هم خودکار «مدرس» می‌شود (مگر این‌که مدیر باشد).
    """
    if not created or raw:
        return
    profile, _ = Profile.objects.get_or_create(user=instance.user)
    if profile.role == Profile.STUDENT:
        profile.role = Profile.INSTRUCTOR
        profile.save(update_fields=['role'])
