import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0002_consultationrequest"),
    ]

    operations = [
        migrations.CreateModel(
            name="Lesson",
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
                ("title", models.CharField(max_length=200, verbose_name="عنوان درس")),
                (
                    "description",
                    models.TextField(blank=True, verbose_name="توضیحات درس"),
                ),
                (
                    "content",
                    models.TextField(blank=True, verbose_name="محتوای آموزشی (متن)"),
                ),
                (
                    "content_url",
                    models.URLField(
                        blank=True,
                        max_length=500,
                        verbose_name="آدرس محتوا (ویدیو / فایل / لینک)",
                    ),
                ),
                (
                    "order",
                    models.PositiveIntegerField(default=1, verbose_name="ترتیب نمایش"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lessons",
                        to="courses.course",
                        verbose_name="دوره",
                    ),
                ),
            ],
            options={
                "verbose_name": "درس",
                "verbose_name_plural": "درس‌ها",
                "ordering": ["order", "id"],
            },
        ),
    ]
