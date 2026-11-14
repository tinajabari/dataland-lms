"""
ساخت داده‌ی نمایشی برای دمو و تحویل پروژه:

    python manage.py seed_demo

چند کاربر (مدیر، مدرس، دانشجو)، دسته‌بندی، دوره، درس و ثبت‌نام می‌سازد.
چند بار اجرا کردنش مشکلی ندارد (تکراری نمی‌سازد).
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.roles import ADMIN, INSTRUCTOR, STUDENT, set_role
from courses.models import Category, Course, Enrollment, Instructor, Lesson, Student

User = get_user_model()

PASSWORD = 'Demo@12345'
ADMIN_PASSWORD = 'Admin@12345'


class Command(BaseCommand):
    help = 'ساخت داده‌ی نمایشی (کاربران، دوره‌ها، درس‌ها و ثبت‌نام‌ها)'

    def _user(self, username, first, last, role, password=PASSWORD):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'first_name': first, 'last_name': last,
                      'email': f'{username}@example.com'},
        )
        if created:
            user.set_password(password)
            user.save()
        set_role(user, role)
        return user

    def handle(self, *args, **options):
        # --- کاربران ---
        self._user('admin', 'مدیر', 'سیستم', ADMIN, ADMIN_PASSWORD)
        t1 = self._user('teacher1', 'علی', 'احمدی', INSTRUCTOR)
        t2 = self._user('teacher2', 'سارا', 'محمدی', INSTRUCTOR)
        students = [
            self._user('student1', 'نرگس', 'رضایی', STUDENT),
            self._user('student2', 'امیر', 'کریمی', STUDENT),
            self._user('student3', 'مینا', 'صادقی', STUDENT),
        ]

        inst1 = Instructor.objects.get(user=t1)
        inst1.specialty = 'برنامه‌نویسی پایتون و جنگو'
        inst1.bio = 'بیش از ده سال تجربه‌ی تدریس و توسعه‌ی نرم‌افزار.'
        inst1.save()
        inst2 = Instructor.objects.get(user=t2)
        inst2.specialty = 'پایگاه داده و تحلیل داده'
        inst2.bio = 'متخصص SQL Server و PostgreSQL.'
        inst2.save()

        # --- دسته‌بندی و دوره‌ها ---
        programming, _ = Category.objects.get_or_create(name='برنامه‌نویسی')
        data, _ = Category.objects.get_or_create(name='داده')

        today = timezone.localdate()
        python_course, _ = Course.objects.get_or_create(
            slug='python-basics',
            defaults=dict(
                title='آموزش پایتون از صفر', instructor=inst1, category=programming,
                level='beginner', price=0, capacity=30,
                short_description='یادگیری پایتون برای مبتدی‌ها',
                description='در این دوره از متغیرها و شرط‌ها شروع می‌کنیم و تا توابع و فایل‌ها پیش می‌رویم.',
                start_date=today + timedelta(days=14),
            ),
        )
        sql_course, _ = Course.objects.get_or_create(
            slug='sql-fundamentals',
            defaults=dict(
                title='مبانی پایگاه داده و SQL', instructor=inst2, category=data,
                level='intermediate', price=1500000, capacity=2,
                short_description='ظرفیت این دوره عمداً ۲ نفر است تا «تکمیل ظرفیت» را ببینید',
                description='طراحی جدول‌ها، کوئری‌نویسی و ایندکس‌ها.',
                start_date=today - timedelta(days=7),  # شروع شده → لغو ثبت‌نام ممکن نیست
            ),
        )
        Course.objects.get_or_create(
            slug='django-advanced',
            defaults=dict(
                title='جنگوی پیشرفته (غیرفعال)', instructor=inst1, category=programming,
                level='advanced', price=2500000, capacity=20, is_active=False,
                description='این دوره غیرفعال است و فقط مدرس و مدیر آن را می‌بینند.',
            ),
        )

        # --- درس‌ها ---
        if not python_course.lessons.exists():
            Lesson.objects.bulk_create([
                Lesson(course=python_course, order=1, title='معرفی و نصب پایتون',
                       description='آشنایی با زبان و محیط کار',
                       content='پایتون را از سایت رسمی نصب کنید و با دستور python --version نصب را بررسی کنید.'),
                Lesson(course=python_course, order=2, title='متغیرها و انواع داده',
                       description='عدد، رشته و بولین',
                       content='متغیر نامی است برای نگهداری یک مقدار.\nمثال: x = 10'),
                Lesson(course=python_course, order=3, title='شرط‌ها و حلقه‌ها',
                       description='if / for / while',
                       content='با if تصمیم می‌گیریم و با for و while تکرار می‌کنیم.'),
                Lesson(course=python_course, order=4, title='مستندات رسمی پایتون',
                       description='منبع مطالعه‌ی تکمیلی',
                       content_url='https://docs.python.org/3/tutorial/'),
            ])
        if not sql_course.lessons.exists():
            Lesson.objects.bulk_create([
                Lesson(course=sql_course, order=1, title='جدول و کلید اصلی',
                       content='هر جدول یک کلید اصلی یکتا دارد.'),
                Lesson(course=sql_course, order=2, title='دستور SELECT',
                       content='SELECT * FROM students;'),
            ])

        # --- ثبت‌نام‌ها ---
        for student_user, course in [
            (students[0], python_course),
            (students[1], sql_course),
            (students[2], sql_course),   # ظرفیت sql_course (۲ نفر) را پر می‌کند
        ]:
            student, _ = Student.objects.get_or_create(user=student_user)
            Enrollment.objects.get_or_create(
                student=student, course=course, defaults={'status': 'approved'}
            )

        self.stdout.write(self.style.SUCCESS('داده‌ی نمایشی ساخته شد.'))
        self.stdout.write(
            '\nحساب‌های نمایشی:\n'
            f'  مدیر    : admin     / {ADMIN_PASSWORD}\n'
            f'  مدرس    : teacher1  / {PASSWORD}   (و teacher2)\n'
            f'  دانشجو  : student1  / {PASSWORD}   (و student2, student3)\n'
        )
