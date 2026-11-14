from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class Instructor(models.Model):
    """پروفایل استاد - وصل به یوزر جنگو برای لاگین"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='instructor_profile')
    bio = models.TextField(blank=True, verbose_name='بیوگرافی')
    specialty = models.CharField(max_length=200, blank=True, verbose_name='تخصص')
    photo = models.ImageField(upload_to='instructors/', blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = 'استاد'
        verbose_name_plural = 'اساتید'

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name='دسته‌بندی')

    class Meta:
        verbose_name = 'دسته‌بندی'
        verbose_name_plural = 'دسته‌بندی‌ها'

    def __str__(self):
        return self.name


class Course(models.Model):
    LEVEL_CHOICES = [
        ('beginner', 'مقدماتی'),
        ('intermediate', 'متوسط'),
        ('advanced', 'پیشرفته'),
    ]

    title = models.CharField(max_length=200, verbose_name='عنوان دوره')
    slug = models.SlugField(unique=True, allow_unicode=True)
    description = models.TextField(verbose_name='توضیحات دوره')
    short_description = models.CharField(max_length=300, blank=True, verbose_name='توضیح کوتاه')
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE, related_name='courses', verbose_name='استاد')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='courses')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='beginner')
    price = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name='قیمت (تومان)')
    capacity = models.PositiveIntegerField(default=30, verbose_name='ظرفیت')
    cover_image = models.ImageField(upload_to='courses/', blank=True, null=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True, verbose_name='فعال / در حال ثبت‌نام')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'دوره'
        verbose_name_plural = 'دوره‌ها'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def enrolled_count(self):
        return self.enrollments.filter(status='approved').count()

    @property
    def remaining_capacity(self):
        return self.capacity - self.enrolled_count

    @property
    def is_full(self):
        return self.remaining_capacity <= 0


class Student(models.Model):
    """پروفایل دانشجو - وصل به یوزر جنگو برای لاگین"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    national_code = models.CharField(max_length=10, blank=True, verbose_name='کد ملی')
    phone = models.CharField(max_length=20, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    courses = models.ManyToManyField(Course, through='Enrollment', related_name='students')

    class Meta:
        verbose_name = 'دانشجو'
        verbose_name_plural = 'دانشجویان'

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Enrollment(models.Model):
    """جدول واسط ثبت‌نام"""
    STATUS_CHOICES = [
        ('pending', 'در انتظار تایید'),
        ('approved', 'تایید شده'),
        ('rejected', 'رد شده'),
        ('cancelled', 'لغو شده'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    registered_at = models.DateTimeField(auto_now_add=True)
    score = models.DecimalField(
        max_digits=4, decimal_places=1, null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(20)]
    )

    class Meta:
        verbose_name = 'ثبت‌نام'
        verbose_name_plural = 'ثبت‌نام‌ها'
        unique_together = ('student', 'course')

    def __str__(self):
        return f'{self.student} - {self.course} ({self.get_status_display()})'

    @property
    def is_current(self):
        """ثبت‌نام فعال (در انتظار یا تایید شده) - یعنی لغو/رد نشده."""
        return self.status in ('pending', 'approved')

    @property
    def can_cancel(self):
        """
        قانون لغو ثبت‌نام: تا قبل از شروع دوره مجاز است.
        اگر تاریخ شروع دوره ثبت نشده باشد هم لغو مجاز است.
        """
        if not self.is_current:
            return False
        start = self.course.start_date
        return start is None or start > timezone.localdate()


class Lesson(models.Model):
    """درس: هر دوره چند درس دارد که با فیلد order ترتیب نمایش آن‌ها مشخص می‌شود."""
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name='lessons', verbose_name='دوره'
    )
    title = models.CharField(max_length=200, verbose_name='عنوان درس')
    description = models.TextField(blank=True, verbose_name='توضیحات درس')
    content = models.TextField(blank=True, verbose_name='محتوای آموزشی (متن)')
    content_url = models.URLField(
        blank=True, max_length=500, verbose_name='آدرس محتوا (ویدیو / فایل / لینک)'
    )
    order = models.PositiveIntegerField(default=1, verbose_name='ترتیب نمایش')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'درس'
        verbose_name_plural = 'درس‌ها'
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.course} - {self.order}. {self.title}'

    @property
    def is_video_file(self):
        """اگر آدرس محتوا یک فایل ویدیویی باشد، در صفحه درس پخش‌کننده نمایش داده می‌شود."""
        return self.content_url.lower().split('?')[0].endswith(('.mp4', '.webm', '.ogg'))


class ConsultationRequest(models.Model):
    """پیام‌های دکمه «مشاوره رایگان» که دانشجو از سایت می‌فرسته"""
    full_name = models.CharField(max_length=150, verbose_name='نام و نام خانوادگی')
    phone = models.CharField(max_length=20, verbose_name='شماره تماس')
    message = models.TextField(blank=True, verbose_name='پیام')
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False, verbose_name='خوانده شده')

    class Meta:
        verbose_name = 'درخواست مشاوره'
        verbose_name_plural = 'درخواست‌های مشاوره'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.full_name} - {self.phone}'
