from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import Count, Max, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.roles import (
    ADMIN, INSTRUCTOR, STUDENT,
    can_manage_course, get_role, role_required,
)

from .forms import ConsultationForm, CourseForm, LessonForm
from .models import Category, Course, Enrollment, Instructor, Lesson, Student
from .sms import send_admin_sms


# ---------------------------------------------------------------------------
# توابع کمکی
# ---------------------------------------------------------------------------

def _manageable_course_or_403(request, slug):
    """دوره را برمی‌گرداند؛ اگر کاربر حق مدیریت آن را نداشته باشد خطای ۴۰۳ می‌دهد."""
    course = get_object_or_404(
        Course.objects.select_related('instructor__user', 'category'), slug=slug
    )
    if not can_manage_course(request.user, course):
        raise PermissionDenied
    return course


def _manageable_lesson_or_403(request, pk):
    lesson = get_object_or_404(
        Lesson.objects.select_related('course__instructor__user'), pk=pk
    )
    if not can_manage_course(request.user, lesson.course):
        raise PermissionDenied
    return lesson


def _student_enrollment(user, course):
    """ثبت‌نام این کاربر (اگر دانشجو باشد) در این دوره؛ در غیر این صورت None."""
    if get_role(user) != STUDENT:
        return None
    return Enrollment.objects.filter(student__user=user, course=course).first()


# ---------------------------------------------------------------------------
# صفحه اصلی و مشاوره
# ---------------------------------------------------------------------------

def home_view(request):
    featured_courses = Course.objects.filter(is_active=True).select_related('instructor__user')[:4]
    return render(request, 'courses/home.html', {'featured_courses': featured_courses})


def consultation_submit_view(request):
    if request.method == 'POST':
        form = ConsultationForm(request.POST)
        if form.is_valid():
            consultation = form.save()
            messages.success(request, 'پیامت با موفقیت ثبت شد؛ به‌زودی باهات تماس می‌گیریم. ✅')
            send_admin_sms(
                f"درخواست مشاوره جدید:\n"
                f"نام: {consultation.full_name}\n"
                f"تماس: {consultation.phone}\n"
                f"پیام: {consultation.message or '-'}"
            )
        else:
            messages.error(request, 'لطفاً نام و شماره تماس رو درست وارد کن.')
    return redirect(request.META.get('HTTP_REFERER', 'home'))


# ---------------------------------------------------------------------------
# اساتید
# ---------------------------------------------------------------------------

def instructor_list_view(request):
    instructors = Instructor.objects.select_related('user').prefetch_related('courses')
    return render(request, 'courses/instructor_list.html', {'instructors': instructors})


def instructor_detail_view(request, pk):
    instructor = get_object_or_404(Instructor, pk=pk)
    courses = instructor.courses.filter(is_active=True)
    return render(request, 'courses/instructor_detail.html', {
        'instructor': instructor,
        'courses': courses,
    })


# ---------------------------------------------------------------------------
# مدیریت دوره‌ها: مشاهده فهرست و جزئیات
# ---------------------------------------------------------------------------

def course_list_view(request):
    """
    فهرست دوره‌ها.
    - دانشجو/مهمان: فقط دوره‌های فعال
    - مدرس: دوره‌های فعال + همه‌ی دوره‌های خودش (حتی غیرفعال)
    - مدیر: همه‌ی دوره‌ها
    """
    role = get_role(request.user)
    courses = Course.objects.select_related('instructor__user', 'category')
    if role == ADMIN:
        pass
    elif role == INSTRUCTOR:
        courses = courses.filter(Q(is_active=True) | Q(instructor__user=request.user))
    else:
        courses = courses.filter(is_active=True)

    q = request.GET.get('q', '').strip()
    if q:
        courses = courses.filter(Q(title__icontains=q) | Q(description__icontains=q))

    category_id = request.GET.get('category', '')
    selected_category = int(category_id) if category_id.isdigit() else None
    if selected_category:
        courses = courses.filter(category_id=selected_category)

    return render(request, 'courses/course_list.html', {
        'courses': courses,
        'categories': Category.objects.all(),
        'selected_category': selected_category,
        'q': q,
    })


def course_detail_view(request, slug):
    course = get_object_or_404(
        Course.objects.select_related('instructor__user', 'category'), slug=slug
    )
    can_manage = can_manage_course(request.user, course)
    if not course.is_active and not can_manage:
        raise Http404

    role = get_role(request.user)
    enrollment = _student_enrollment(request.user, course)
    has_current_enrollment = bool(enrollment and enrollment.is_current)
    has_lesson_access = can_manage or bool(enrollment and enrollment.status == 'approved')
    # دانشجو وقتی می‌تواند ثبت‌نام کند که دوره فعال و دارای ظرفیت باشد
    # و یا ثبت‌نامی نداشته باشد یا ثبت‌نام قبلی‌اش را لغو کرده باشد.
    can_enroll = (
        role == STUDENT
        and course.is_active
        and not course.is_full
        and (enrollment is None or enrollment.status == 'cancelled')
    )

    return render(request, 'courses/course_detail.html', {
        'course': course,
        'lessons': course.lessons.all(),
        'can_manage': can_manage,
        'enrollment': enrollment,
        'has_current_enrollment': has_current_enrollment,
        'has_lesson_access': has_lesson_access,
        'can_enroll': can_enroll,
    })


@role_required(ADMIN, INSTRUCTOR)
def manage_courses_view(request):
    """پنل مدیریت دوره‌ها: مدرس دوره‌های خودش را می‌بیند و مدیر همه را."""
    courses = Course.objects.select_related('instructor__user', 'category').annotate(
        student_count=Count('enrollments', filter=Q(enrollments__status='approved'), distinct=True),
        lesson_count=Count('lessons', distinct=True),
    )
    if get_role(request.user) == INSTRUCTOR:
        courses = courses.filter(instructor__user=request.user)
    return render(request, 'courses/course_manage.html', {'courses': courses})


# ---------------------------------------------------------------------------
# مدیریت دوره‌ها: ایجاد / ویرایش / حذف / فعال‌سازی
# ---------------------------------------------------------------------------

@role_required(ADMIN, INSTRUCTOR)
def course_create_view(request):
    is_admin = get_role(request.user) == ADMIN
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES, can_choose_instructor=is_admin)
        if form.is_valid():
            course = form.save(commit=False)
            if not is_admin:
                course.instructor, _ = Instructor.objects.get_or_create(user=request.user)
            course.save()
            messages.success(request, 'دوره با موفقیت ایجاد شد. حالا می‌توانید درس‌ها را اضافه کنید.')
            return redirect('courses:course_detail', slug=course.slug)
    else:
        form = CourseForm(can_choose_instructor=is_admin)
    return render(request, 'courses/course_form.html', {'form': form, 'mode': 'create'})


@login_required
def course_update_view(request, slug):
    course = _manageable_course_or_403(request, slug)
    is_admin = get_role(request.user) == ADMIN
    if request.method == 'POST':
        form = CourseForm(
            request.POST, request.FILES, instance=course, can_choose_instructor=is_admin
        )
        if form.is_valid():
            course = form.save()
            messages.success(request, 'اطلاعات دوره ذخیره شد.')
            return redirect('courses:course_detail', slug=course.slug)
    else:
        form = CourseForm(instance=course, can_choose_instructor=is_admin)
    return render(request, 'courses/course_form.html', {
        'form': form, 'mode': 'edit', 'course': course,
    })


@login_required
@require_POST
def course_toggle_active_view(request, slug):
    """غیرفعال/فعال کردن دوره (بدون حذف اطلاعات و ثبت‌نام‌ها)."""
    course = _manageable_course_or_403(request, slug)
    course.is_active = not course.is_active
    course.save(update_fields=['is_active'])
    state = 'فعال' if course.is_active else 'غیرفعال'
    messages.success(request, f'دوره «{course.title}» {state} شد.')
    if request.POST.get('next') == 'manage':
        return redirect('courses:course_manage')
    return redirect('courses:course_detail', slug=course.slug)


@login_required
def course_delete_view(request, slug):
    course = _manageable_course_or_403(request, slug)
    if request.method == 'POST':
        title = course.title
        course.delete()
        messages.success(request, f'دوره «{title}» حذف شد.')
        return redirect('courses:course_manage')
    return render(request, 'courses/course_confirm_delete.html', {
        'course': course,
        'lesson_count': course.lessons.count(),
        'enrollment_count': course.enrollments.count(),
    })


@login_required
def course_students_view(request, slug):
    """فهرست دانشجوهای یک دوره (فقط مدرسِ همان دوره یا مدیر)."""
    course = _manageable_course_or_403(request, slug)
    enrollments = course.enrollments.select_related('student__user__profile').order_by('-registered_at')
    return render(request, 'courses/course_students.html', {
        'course': course,
        'enrollments': enrollments,
        'active_count': sum(1 for e in enrollments if e.is_current),
    })


# ---------------------------------------------------------------------------
# ثبت‌نام دانشجو در دوره
# ---------------------------------------------------------------------------

@require_POST
@role_required(STUDENT)
def enroll_course_view(request, slug):
    course = get_object_or_404(Course, slug=slug, is_active=True)
    student, _ = Student.objects.get_or_create(user=request.user)
    enrollment = Enrollment.objects.filter(student=student, course=course).first()

    if enrollment and enrollment.is_current:
        # جلوگیری از ثبت‌نام تکراری
        messages.info(request, 'شما قبلاً در این دوره ثبت‌نام کرده‌اید.')
    elif enrollment and enrollment.status == 'rejected':
        messages.error(request, 'ثبت‌نام شما در این دوره رد شده است؛ با مدیر تماس بگیرید.')
    elif course.is_full:
        messages.error(request, 'ظرفیت این دوره تکمیل شده است.')
    elif enrollment:
        # ثبت‌نام قبلاً لغو شده بود → دوباره فعال می‌شود
        enrollment.status = 'approved'
        enrollment.save(update_fields=['status'])
        messages.success(request, 'ثبت‌نام شما دوباره فعال شد.')
    else:
        try:
            with transaction.atomic():
                Enrollment.objects.create(student=student, course=course, status='approved')
            messages.success(request, 'ثبت‌نام شما با موفقیت انجام شد.')
        except IntegrityError:
            # دو کلیک هم‌زمان: محدودیت یکتا در دیتابیس جلوی تکراری شدن را می‌گیرد
            messages.info(request, 'شما قبلاً در این دوره ثبت‌نام کرده‌اید.')
    return redirect('courses:course_detail', slug=slug)


@login_required
@require_POST
def enrollment_cancel_view(request, pk):
    """
    لغو ثبت‌نام.
    - دانشجو فقط ثبت‌نام خودش را و فقط تا قبل از شروع دوره می‌تواند لغو کند.
    - مدرسِ دوره / مدیر می‌تواند هر ثبت‌نامِ فعال را لغو کند.
    """
    enrollment = get_object_or_404(
        Enrollment.objects.select_related('course__instructor__user', 'student__user'), pk=pk
    )
    course = enrollment.course
    is_owner = enrollment.student.user_id == request.user.id
    is_manager = can_manage_course(request.user, course)
    if not (is_owner or is_manager):
        raise PermissionDenied

    if not enrollment.is_current:
        messages.info(request, 'این ثبت‌نام قبلاً لغو یا رد شده است.')
    elif is_manager or enrollment.can_cancel:
        enrollment.status = 'cancelled'
        enrollment.save(update_fields=['status'])
        messages.success(request, 'ثبت‌نام لغو شد.')
    else:
        messages.error(request, 'لغو ثبت‌نام بعد از شروع دوره امکان‌پذیر نیست.')

    target = request.POST.get('next')
    if target == 'detail':
        return redirect('courses:course_detail', slug=course.slug)
    if target == 'students' and is_manager:
        return redirect('courses:course_students', slug=course.slug)
    if is_owner:
        return redirect('courses:my_courses')
    return redirect('courses:course_students', slug=course.slug)


@role_required(STUDENT)
def my_courses_view(request):
    student, _ = Student.objects.get_or_create(user=request.user)
    enrollments = (
        Enrollment.objects.filter(student=student)
        .select_related('course__instructor__user')
        .order_by('-registered_at')
    )
    return render(request, 'courses/my_courses.html', {'enrollments': enrollments})


# ---------------------------------------------------------------------------
# درس‌ها و محتوای آموزشی
# ---------------------------------------------------------------------------

def lesson_detail_view(request, pk):
    """
    نمایش درس. دسترسی: مدرسِ دوره، مدیر، یا دانشجوی ثبت‌نام‌شده (تایید شده).
    بقیه به صفحه‌ی دوره هدایت می‌شوند.
    """
    lesson = get_object_or_404(
        Lesson.objects.select_related('course__instructor__user'), pk=pk
    )
    course = lesson.course
    can_manage = can_manage_course(request.user, course)
    if not course.is_active and not can_manage:
        raise Http404

    enrollment = _student_enrollment(request.user, course)
    if not (can_manage or (enrollment and enrollment.status == 'approved')):
        if request.user.is_authenticated:
            messages.error(request, 'برای دیدن محتوای درس‌ها باید در این دوره ثبت‌نام کنید.')
        else:
            messages.error(request, 'برای دیدن محتوای درس‌ها ابتدا وارد شوید و در دوره ثبت‌نام کنید.')
        return redirect('courses:course_detail', slug=course.slug)

    lessons = list(course.lessons.all())
    index = next((i for i, item in enumerate(lessons) if item.pk == lesson.pk), 0)
    return render(request, 'courses/lesson_detail.html', {
        'course': course,
        'lesson': lesson,
        'lessons': lessons,
        'prev_lesson': lessons[index - 1] if index > 0 else None,
        'next_lesson': lessons[index + 1] if index < len(lessons) - 1 else None,
        'can_manage': can_manage,
    })


@login_required
def lesson_create_view(request, slug):
    course = _manageable_course_or_403(request, slug)
    if request.method == 'POST':
        form = LessonForm(request.POST)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.course = course
            lesson.save()
            messages.success(request, 'درس جدید اضافه شد.')
            return redirect('courses:course_detail', slug=course.slug)
    else:
        next_order = (course.lessons.aggregate(m=Max('order'))['m'] or 0) + 1
        form = LessonForm(initial={'order': next_order})
    return render(request, 'courses/lesson_form.html', {
        'form': form, 'course': course, 'mode': 'create',
    })


@login_required
def lesson_update_view(request, pk):
    lesson = _manageable_lesson_or_403(request, pk)
    if request.method == 'POST':
        form = LessonForm(request.POST, instance=lesson)
        if form.is_valid():
            form.save()
            messages.success(request, 'درس ذخیره شد.')
            return redirect('courses:course_detail', slug=lesson.course.slug)
    else:
        form = LessonForm(instance=lesson)
    return render(request, 'courses/lesson_form.html', {
        'form': form, 'course': lesson.course, 'lesson': lesson, 'mode': 'edit',
    })


@login_required
def lesson_delete_view(request, pk):
    lesson = _manageable_lesson_or_403(request, pk)
    if request.method == 'POST':
        slug = lesson.course.slug
        lesson.delete()
        messages.success(request, 'درس حذف شد.')
        return redirect('courses:course_detail', slug=slug)
    return render(request, 'courses/lesson_confirm_delete.html', {
        'lesson': lesson, 'course': lesson.course,
    })
