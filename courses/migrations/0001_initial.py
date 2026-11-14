# Generated for courses app

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100, verbose_name="دسته‌بندی")),
            ],
            options={
                "verbose_name": "دسته‌بندی",
                "verbose_name_plural": "دسته‌بندی‌ها",
            },
        ),
        migrations.CreateModel(
            name="Instructor",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("bio", models.TextField(blank=True, verbose_name="بیوگرافی")),
                (
                    "specialty",
                    models.CharField(blank=True, max_length=200, verbose_name="تخصص"),
                ),
                (
                    "photo",
                    models.ImageField(blank=True, null=True, upload_to="instructors/"),
                ),
                ("phone", models.CharField(blank=True, max_length=20)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="instructor_profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "استاد",
                "verbose_name_plural": "اساتید",
            },
        ),
        migrations.CreateModel(
            name="Student",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "national_code",
                    models.CharField(blank=True, max_length=10, verbose_name="کد ملی"),
                ),
                ("phone", models.CharField(blank=True, max_length=20)),
                ("birth_date", models.DateField(blank=True, null=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="student_profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "دانشجو",
                "verbose_name_plural": "دانشجویان",
            },
        ),
        migrations.CreateModel(
            name="Course",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=200, verbose_name="عنوان دوره")),
                ("slug", models.SlugField(allow_unicode=True, unique=True)),
                ("description", models.TextField(verbose_name="توضیحات دوره")),
                (
                    "short_description",
                    models.CharField(
                        blank=True, max_length=300, verbose_name="توضیح کوتاه"
                    ),
                ),
                (
                    "level",
                    models.CharField(
                        choices=[
                            ("beginner", "مقدماتی"),
                            ("intermediate", "متوسط"),
                            ("advanced", "پیشرفته"),
                        ],
                        default="beginner",
                        max_length=20,
                    ),
                ),
                (
                    "price",
                    models.DecimalField(
                        decimal_places=0,
                        default=0,
                        max_digits=10,
                        verbose_name="قیمت (تومان)",
                    ),
                ),
                ("capacity", models.PositiveIntegerField(default=30, verbose_name="ظرفیت")),
                (
                    "cover_image",
                    models.ImageField(blank=True, null=True, upload_to="courses/"),
                ),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                (
                    "is_active",
                    models.BooleanField(
                        default=True, verbose_name="فعال / در حال ثبت‌نام"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "category",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="courses",
                        to="courses.category",
                    ),
                ),
                (
                    "instructor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="courses",
                        to="courses.instructor",
                        verbose_name="استاد",
                    ),
                ),
            ],
            options={
                "verbose_name": "دوره",
                "verbose_name_plural": "دوره‌ها",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Enrollment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "در انتظار تایید"),
                            ("approved", "تایید شده"),
                            ("rejected", "رد شده"),
                            ("cancelled", "لغو شده"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("registered_at", models.DateTimeField(auto_now_add=True)),
                (
                    "score",
                    models.DecimalField(
                        blank=True,
                        decimal_places=1,
                        max_digits=4,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(20),
                        ],
                    ),
                ),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="enrollments",
                        to="courses.course",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="enrollments",
                        to="courses.student",
                    ),
                ),
            ],
            options={
                "verbose_name": "ثبت‌نام",
                "verbose_name_plural": "ثبت‌نام‌ها",
            },
        ),
        migrations.AddField(
            model_name="student",
            name="courses",
            field=models.ManyToManyField(
                related_name="students", through="courses.Enrollment", to="courses.course"
            ),
        ),
        migrations.AlterUniqueTogether(
            name="enrollment",
            unique_together={("student", "course")},
        ),
    ]
