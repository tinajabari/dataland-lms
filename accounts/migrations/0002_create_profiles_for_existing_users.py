from django.conf import settings
from django.db import migrations


def create_profiles(apps, schema_editor):
    """برای کاربران قبلی (قبل از افزودن نقش‌ها) پروفایل نقش می‌سازد."""
    User = apps.get_model(*settings.AUTH_USER_MODEL.split('.'))
    Profile = apps.get_model('accounts', 'Profile')
    Instructor = apps.get_model('courses', 'Instructor')

    instructor_user_ids = set(Instructor.objects.values_list('user_id', flat=True))
    for user in User.objects.all():
        if Profile.objects.filter(user_id=user.pk).exists():
            continue
        if user.is_superuser:
            role = 'admin'
        elif user.pk in instructor_user_ids:
            role = 'instructor'
        else:
            role = 'student'
        Profile.objects.create(user_id=user.pk, role=role)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('courses', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_profiles, migrations.RunPython.noop),
    ]
