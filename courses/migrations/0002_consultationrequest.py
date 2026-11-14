from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ConsultationRequest",
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
                    "full_name",
                    models.CharField(
                        max_length=150, verbose_name="نام و نام خانوادگی"
                    ),
                ),
                ("phone", models.CharField(max_length=20, verbose_name="شماره تماس")),
                ("message", models.TextField(blank=True, verbose_name="پیام")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "is_read",
                    models.BooleanField(default=False, verbose_name="خوانده شده"),
                ),
            ],
            options={
                "verbose_name": "درخواست مشاوره",
                "verbose_name_plural": "درخواست‌های مشاوره",
                "ordering": ["-created_at"],
            },
        ),
    ]
