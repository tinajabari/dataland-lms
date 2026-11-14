from django.conf import settings
from django.db import models


class Profile(models.Model):
    """
    پروفایل نقش کاربر در سیستم (LMS).
    نقش‌ها: مدیر، مدرس، دانشجو - مبنای تعیین سطح دسترسی هر کاربر.
    """
    ADMIN = 'admin'
    INSTRUCTOR = 'instructor'
    STUDENT = 'student'
    ROLE_CHOICES = [
        (ADMIN, 'مدیر'),
        (INSTRUCTOR, 'مدرس'),
        (STUDENT, 'دانشجو'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile'
    )
    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default=STUDENT, verbose_name='نقش'
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name='شماره تماس')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'پروفایل کاربر'
        verbose_name_plural = 'پروفایل کاربران'

    def __str__(self):
        return f'{self.user} ({self.get_role_display()})'
