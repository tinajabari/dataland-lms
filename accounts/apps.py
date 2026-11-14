from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "accounts"
    verbose_name = "حساب‌های کاربری"

    def ready(self):
        from django.db.models.signals import post_save

        from courses.models import Instructor
        from . import signals  # noqa: F401  (ثبت سیگنال ساخت پروفایل)

        post_save.connect(
            signals.sync_role_for_new_instructor,
            sender=Instructor,
            dispatch_uid='accounts_sync_role_for_new_instructor',
        )
