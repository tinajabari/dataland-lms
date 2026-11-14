from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.roles import ADMIN, INSTRUCTOR, STUDENT, set_role

from .models import ConsultationRequest, Course, Enrollment, Instructor, Lesson, Student

User = get_user_model()
PW = 'Str0ng-Pass!23'


def make_user(username, role):
    user = User.objects.create_user(username, password=PW, first_name=username.title())
    set_role(user, role)
    return user


class LMSTestCase(TestCase):
    """داده‌ی پایه: مدیر، دو مدرس، دو دانشجو، یک دوره (ظرفیت ۲) و یک درس."""

    def setUp(self):
        self.admin = make_user('admin1', ADMIN)
        self.teacher = make_user('teacher1', INSTRUCTOR)
        self.other_teacher = make_user('teacher2', INSTRUCTOR)
        self.student = make_user('student1', STUDENT)
        self.student2 = make_user('student2', STUDENT)

        self.instructor = Instructor.objects.get(user=self.teacher)
        self.other_instructor = Instructor.objects.get(user=self.other_teacher)

        self.course = Course.objects.create(
            title='پایتون', slug='python', description='توضیح دوره',
            instructor=self.instructor, capacity=2,
        )
        self.lesson = Lesson.objects.create(
            course=self.course, title='درس اول', content='متن درس اول', order=1,
        )

    # --- کمکی‌ها ---
    def login(self, user):
        self.client.force_login(user)

    def enroll_url(self, course=None):
        return reverse('courses:enroll_course', args=[(course or self.course).slug])

    def enroll(self, user, course=None):
        """ثبت‌نام از طریق خود ویو (مثل کلیک دانشجو)."""
        self.login(user)
        return self.client.post(self.enroll_url(course))

    def course_form_data(self, **overrides):
        data = {
            'title': 'دوره جدید من', 'slug': '', 'category': '', 'level': 'beginner',
            'short_description': '', 'description': 'توضیحات دوره', 'price': '0',
            'capacity': '10', 'start_date': '', 'end_date': '', 'is_active': 'on',
        }
        data.update(overrides)
        return data

    def lesson_form_data(self, **overrides):
        data = {'title': 'درس تازه', 'description': '', 'content': 'متن', 'content_url': '', 'order': '2'}
        data.update(overrides)
        return data


# ---------------------------------------------------------------------------
# ۲. مدیریت دوره‌ها
# ---------------------------------------------------------------------------

class CourseViewTests(LMSTestCase):
    def test_course_list_and_detail_are_public(self):
        self.assertContains(self.client.get(reverse('courses:course_list')), 'پایتون')
        self.assertEqual(self.client.get(reverse('courses:course_detail', args=['python'])).status_code, 200)

    def test_detail_page_renders_for_every_role(self):
        url = reverse('courses:course_detail', args=['python'])
        for user in (None, self.student, self.teacher, self.other_teacher, self.admin):
            if user:
                self.login(user)
            self.assertEqual(self.client.get(url).status_code, 200, msg=user)

    def test_anonymous_sees_login_prompt_and_student_sees_enroll_button(self):
        url = reverse('courses:course_detail', args=['python'])
        self.assertContains(self.client.get(url), reverse('login'))
        self.login(self.student)
        self.assertContains(self.client.get(url), self.enroll_url())

    def test_inactive_course_hidden_from_students_but_visible_to_owner(self):
        self.course.is_active = False
        self.course.save()
        detail = reverse('courses:course_detail', args=['python'])
        self.login(self.student)
        self.assertEqual(self.client.get(detail).status_code, 404)
        self.assertNotIn(self.course, list(self.client.get(reverse('courses:course_list')).context['courses']))
        self.login(self.teacher)
        self.assertEqual(self.client.get(detail).status_code, 200)
        self.assertIn(self.course, list(self.client.get(reverse('courses:course_list')).context['courses']))

    def test_search_filters_courses(self):
        Course.objects.create(title='جاوا', slug='java', description='x', instructor=self.instructor)
        resp = self.client.get(reverse('courses:course_list'), {'q': 'جاوا'})
        titles = [c.title for c in resp.context['courses']]
        self.assertEqual(titles, ['جاوا'])


class CourseCrudTests(LMSTestCase):
    def test_student_cannot_open_create_page(self):
        self.login(self.student)
        self.assertEqual(self.client.get(reverse('courses:course_create')).status_code, 403)

    def test_anonymous_redirected_to_login(self):
        resp = self.client.get(reverse('courses:course_create'))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp['Location'].startswith(reverse('login')))

    def test_instructor_creates_course_and_is_assigned_automatically(self):
        self.login(self.teacher)
        resp = self.client.post(reverse('courses:course_create'), self.course_form_data())
        self.assertEqual(resp.status_code, 302)
        course = Course.objects.get(title='دوره جدید من')
        self.assertEqual(course.instructor, self.instructor)
        self.assertTrue(course.slug)
        # آدرس فارسی دوره هم باید باز شود
        self.assertEqual(self.client.get(reverse('courses:course_detail', args=[course.slug])).status_code, 200)

    def test_reserved_slug_is_avoided(self):
        self.login(self.teacher)
        self.client.post(reverse('courses:course_create'), self.course_form_data(title='new'))
        self.assertEqual(Course.objects.get(title='new').slug, 'new-2')

    def test_admin_must_choose_instructor(self):
        self.login(self.admin)
        resp = self.client.post(reverse('courses:course_create'), self.course_form_data())
        self.assertEqual(resp.status_code, 200)  # خطای فرم: مدرس انتخاب نشده
        self.assertFalse(Course.objects.filter(title='دوره جدید من').exists())

        resp = self.client.post(
            reverse('courses:course_create'),
            self.course_form_data(instructor=str(self.other_instructor.pk)),
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Course.objects.get(title='دوره جدید من').instructor, self.other_instructor)

    def test_capacity_must_be_positive(self):
        self.login(self.teacher)
        resp = self.client.post(reverse('courses:course_create'), self.course_form_data(capacity='0'))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Course.objects.filter(title='دوره جدید من').exists())

    def test_end_date_cannot_precede_start_date(self):
        self.login(self.teacher)
        resp = self.client.post(
            reverse('courses:course_create'),
            self.course_form_data(start_date='2030-05-10', end_date='2030-05-01'),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Course.objects.filter(title='دوره جدید من').exists())

    def test_owner_can_edit_course(self):
        self.login(self.teacher)
        url = reverse('courses:course_update', args=['python'])
        self.assertEqual(self.client.get(url).status_code, 200)
        resp = self.client.post(url, self.course_form_data(title='پایتون پیشرفته', slug='python'))
        self.assertRedirects(resp, reverse('courses:course_detail', args=['python']))
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, 'پایتون پیشرفته')

    def test_other_instructor_and_student_cannot_edit(self):
        url = reverse('courses:course_update', args=['python'])
        for user in (self.other_teacher, self.student):
            self.login(user)
            self.assertEqual(self.client.get(url).status_code, 403)
            self.assertEqual(
                self.client.post(url, self.course_form_data(title='هک شد', slug='python')).status_code, 403
            )
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, 'پایتون')

    def test_admin_can_reassign_instructor(self):
        self.login(self.admin)
        url = reverse('courses:course_update', args=['python'])
        resp = self.client.post(
            url, self.course_form_data(title='پایتون', slug='python', instructor=str(self.other_instructor.pk))
        )
        self.assertEqual(resp.status_code, 302)
        self.course.refresh_from_db()
        self.assertEqual(self.course.instructor, self.other_instructor)

    def test_toggle_active(self):
        url = reverse('courses:course_toggle_active', args=['python'])
        self.login(self.student)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.login(self.teacher)
        self.assertEqual(self.client.get(url).status_code, 405)  # فقط POST
        self.client.post(url)
        self.course.refresh_from_db()
        self.assertFalse(self.course.is_active)
        self.client.post(url)
        self.course.refresh_from_db()
        self.assertTrue(self.course.is_active)

    def test_delete_needs_confirmation_and_permission(self):
        url = reverse('courses:course_delete', args=['python'])
        self.login(self.other_teacher)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.assertTrue(Course.objects.filter(slug='python').exists())

        self.login(self.teacher)
        self.assertEqual(self.client.get(url).status_code, 200)       # صفحه تایید
        self.assertTrue(Course.objects.filter(slug='python').exists())  # GET چیزی حذف نمی‌کند
        resp = self.client.post(url)
        self.assertRedirects(resp, reverse('courses:course_manage'))
        self.assertFalse(Course.objects.filter(slug='python').exists())

    def test_manage_page_scopes_by_role(self):
        Course.objects.create(title='دوره دیگر', slug='other', description='x', instructor=self.other_instructor)
        manage = reverse('courses:course_manage')
        self.login(self.teacher)
        self.assertEqual([c.slug for c in self.client.get(manage).context['courses']], ['python'])
        self.login(self.admin)
        self.assertEqual(len(self.client.get(manage).context['courses']), 2)
        self.login(self.student)
        self.assertEqual(self.client.get(manage).status_code, 403)


# ---------------------------------------------------------------------------
# ۳. درس‌ها و محتوا
# ---------------------------------------------------------------------------

class LessonTests(LMSTestCase):
    def test_lessons_are_ordered(self):
        Lesson.objects.create(course=self.course, title='سوم', content='x', order=3)
        Lesson.objects.create(course=self.course, title='دوم', content='x', order=2)
        self.assertEqual(list(self.course.lessons.values_list('order', flat=True)), [1, 2, 3])
        resp = self.client.get(reverse('courses:course_detail', args=['python']))
        self.assertEqual([l.order for l in resp.context['lessons']], [1, 2, 3])

    def test_owner_creates_lesson_with_next_order(self):
        self.login(self.teacher)
        url = reverse('courses:lesson_create', args=['python'])
        self.assertEqual(self.client.get(url).context['form'].initial['order'], 2)
        resp = self.client.post(url, self.lesson_form_data())
        self.assertRedirects(resp, reverse('courses:course_detail', args=['python']))
        self.assertTrue(Lesson.objects.filter(course=self.course, title='درس تازه', order=2).exists())

    def test_lesson_needs_content_or_url(self):
        self.login(self.teacher)
        resp = self.client.post(
            reverse('courses:lesson_create', args=['python']),
            self.lesson_form_data(content='', content_url=''),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Lesson.objects.filter(title='درس تازه').exists())

    def test_lesson_with_url_only_is_valid_and_bad_url_rejected(self):
        self.login(self.teacher)
        url = reverse('courses:lesson_create', args=['python'])
        self.client.post(url, self.lesson_form_data(content='', content_url='https://example.com/video.mp4'))
        lesson = Lesson.objects.get(title='درس تازه')
        self.assertTrue(lesson.is_video_file)
        resp = self.client.post(url, self.lesson_form_data(title='بد', content='', content_url='not a url'))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Lesson.objects.filter(title='بد').exists())

    def test_only_course_owner_or_admin_can_create_lessons(self):
        url = reverse('courses:lesson_create', args=['python'])
        for user in (self.student, self.other_teacher):
            self.login(user)
            self.assertEqual(self.client.post(url, self.lesson_form_data()).status_code, 403)
        self.assertFalse(Lesson.objects.filter(title='درس تازه').exists())
        self.login(self.admin)
        self.assertEqual(self.client.post(url, self.lesson_form_data()).status_code, 302)

    def test_update_and_delete_lesson(self):
        self.login(self.teacher)
        edit = reverse('courses:lesson_update', args=[self.lesson.pk])
        self.client.post(edit, self.lesson_form_data(title='عنوان جدید', order='1'))
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.title, 'عنوان جدید')

        delete = reverse('courses:lesson_delete', args=[self.lesson.pk])
        self.assertEqual(self.client.get(delete).status_code, 200)
        self.assertTrue(Lesson.objects.filter(pk=self.lesson.pk).exists())
        self.client.post(delete)
        self.assertFalse(Lesson.objects.filter(pk=self.lesson.pk).exists())

    def test_other_instructor_cannot_edit_or_delete_lesson(self):
        self.login(self.other_teacher)
        self.assertEqual(self.client.post(reverse('courses:lesson_update', args=[self.lesson.pk]),
                                          self.lesson_form_data()).status_code, 403)
        self.assertEqual(self.client.post(reverse('courses:lesson_delete', args=[self.lesson.pk])).status_code, 403)
        self.assertTrue(Lesson.objects.filter(pk=self.lesson.pk).exists())

    def test_lesson_content_access_control(self):
        url = reverse('courses:lesson_detail', args=[self.lesson.pk])
        back = reverse('courses:course_detail', args=['python'])

        # مهمان و دانشجوی ثبت‌نام‌نکرده و مدرس دیگر → برمی‌گردند به صفحه دوره
        self.assertRedirects(self.client.get(url), back)
        for user in (self.student, self.other_teacher):
            self.login(user)
            self.assertRedirects(self.client.get(url), back)

        # دانشجوی ثبت‌نام‌شده، مدرس دوره و مدیر → می‌بینند
        self.enroll(self.student)
        self.assertContains(self.client.get(url), 'متن درس اول')
        for user in (self.teacher, self.admin):
            self.login(user)
            self.assertContains(self.client.get(url), 'متن درس اول')

    def test_cancelled_student_loses_lesson_access(self):
        self.enroll(self.student)
        Enrollment.objects.filter(student__user=self.student).update(status='cancelled')
        self.login(self.student)
        resp = self.client.get(reverse('courses:lesson_detail', args=[self.lesson.pk]))
        self.assertEqual(resp.status_code, 302)

    def test_prev_next_navigation(self):
        second = Lesson.objects.create(course=self.course, title='دوم', content='x', order=2)
        third = Lesson.objects.create(course=self.course, title='سوم', content='x', order=3)
        self.login(self.teacher)
        resp = self.client.get(reverse('courses:lesson_detail', args=[second.pk]))
        self.assertEqual(resp.context['prev_lesson'], self.lesson)
        self.assertEqual(resp.context['next_lesson'], third)

    def test_deleting_course_deletes_its_lessons(self):
        self.course.delete()
        self.assertFalse(Lesson.objects.filter(pk=self.lesson.pk).exists())


# ---------------------------------------------------------------------------
# ۴. ثبت‌نام دانشجوها
# ---------------------------------------------------------------------------

class EnrollmentTests(LMSTestCase):
    def test_student_can_enroll(self):
        resp = self.enroll(self.student)
        self.assertRedirects(resp, reverse('courses:course_detail', args=['python']))
        enrollment = Enrollment.objects.get(student__user=self.student, course=self.course)
        self.assertEqual(enrollment.status, 'approved')

    def test_duplicate_enrollment_is_prevented(self):
        self.enroll(self.student)
        self.enroll(self.student)
        self.assertEqual(Enrollment.objects.filter(student__user=self.student, course=self.course).count(), 1)

    def test_enroll_requires_post_and_student_role(self):
        self.login(self.student)
        self.assertEqual(self.client.get(self.enroll_url()).status_code, 405)
        for user in (self.teacher, self.admin):
            self.assertEqual(self.enroll(user).status_code, 403)
        self.assertEqual(Enrollment.objects.count(), 0)

    def test_anonymous_enroll_redirects_to_login(self):
        resp = self.client.post(self.enroll_url())
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp['Location'].startswith(reverse('login')))

    def test_cannot_enroll_in_inactive_course(self):
        self.course.is_active = False
        self.course.save()
        self.assertEqual(self.enroll(self.student).status_code, 404)

    def test_capacity_is_enforced(self):
        student3 = make_user('student3', STUDENT)
        self.enroll(self.student)
        self.enroll(self.student2)
        self.assertTrue(self.course.is_full)
        self.enroll(student3)
        self.assertFalse(Enrollment.objects.filter(student__user=student3).exists())
        self.assertEqual(self.course.enrolled_count, 2)

    def test_my_courses_page(self):
        self.enroll(self.student)
        resp = self.client.get(reverse('courses:my_courses'))
        self.assertContains(resp, 'پایتون')
        self.login(self.student2)
        self.assertNotContains(self.client.get(reverse('courses:my_courses')), 'پایتون')
        self.login(self.teacher)
        self.assertEqual(self.client.get(reverse('courses:my_courses')).status_code, 403)

    def _enrollment(self, user=None):
        return Enrollment.objects.get(student__user=user or self.student, course=self.course)

    def test_cancel_before_course_start(self):
        self.course.start_date = timezone.localdate() + timedelta(days=5)
        self.course.save()
        self.enroll(self.student)
        enrollment = self._enrollment()
        self.assertTrue(enrollment.can_cancel)
        resp = self.client.post(reverse('courses:enrollment_cancel', args=[enrollment.pk]))
        self.assertRedirects(resp, reverse('courses:my_courses'))
        self.assertEqual(self._enrollment().status, 'cancelled')

    def test_cancel_without_start_date_is_allowed(self):
        self.enroll(self.student)
        self.assertTrue(self._enrollment().can_cancel)

    def test_cancel_after_course_start_is_denied(self):
        self.course.start_date = timezone.localdate() - timedelta(days=1)
        self.course.save()
        self.enroll(self.student)
        enrollment = self._enrollment()
        self.assertFalse(enrollment.can_cancel)
        self.client.post(reverse('courses:enrollment_cancel', args=[enrollment.pk]))
        self.assertEqual(self._enrollment().status, 'approved')

    def test_cancelled_student_can_enroll_again_without_duplicate_row(self):
        self.enroll(self.student)
        self.client.post(reverse('courses:enrollment_cancel', args=[self._enrollment().pk]))
        self.assertEqual(self._enrollment().status, 'cancelled')
        self.enroll(self.student)
        self.assertEqual(self._enrollment().status, 'approved')
        self.assertEqual(Enrollment.objects.filter(course=self.course).count(), 1)

    def test_cancelling_frees_capacity(self):
        self.enroll(self.student)
        self.enroll(self.student2)
        self.assertTrue(self.course.is_full)
        self.login(self.student)
        self.client.post(reverse('courses:enrollment_cancel', args=[self._enrollment().pk]))
        self.assertFalse(self.course.is_full)

    def test_student_cannot_cancel_someone_elses_enrollment(self):
        self.enroll(self.student)
        enrollment = self._enrollment()
        self.login(self.student2)
        self.assertEqual(self.client.post(reverse('courses:enrollment_cancel', args=[enrollment.pk])).status_code, 403)
        self.assertEqual(self._enrollment().status, 'approved')

    def test_cancel_requires_post(self):
        self.enroll(self.student)
        self.assertEqual(
            self.client.get(reverse('courses:enrollment_cancel', args=[self._enrollment().pk])).status_code, 405
        )

    def test_course_owner_can_cancel_even_after_start(self):
        self.course.start_date = timezone.localdate() - timedelta(days=3)
        self.course.save()
        self.enroll(self.student)
        enrollment = self._enrollment()
        self.login(self.teacher)
        resp = self.client.post(reverse('courses:enrollment_cancel', args=[enrollment.pk]), {'next': 'students'})
        self.assertRedirects(resp, reverse('courses:course_students', args=['python']))
        self.assertEqual(self._enrollment().status, 'cancelled')

    def test_other_instructor_cannot_cancel_students_of_this_course(self):
        self.enroll(self.student)
        self.login(self.other_teacher)
        resp = self.client.post(reverse('courses:enrollment_cancel', args=[self._enrollment().pk]))
        self.assertEqual(resp.status_code, 403)

    def test_course_student_list_permissions_and_content(self):
        self.enroll(self.student)
        url = reverse('courses:course_students', args=['python'])
        for user in (self.teacher, self.admin):
            self.login(user)
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual([e.student.user for e in resp.context['enrollments']], [self.student])
        for user in (self.other_teacher, self.student):
            self.login(user)
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_student_enrolled_in_several_courses(self):
        other = Course.objects.create(title='جاوا', slug='java', description='x', instructor=self.other_instructor)
        self.enroll(self.student)
        self.enroll(self.student, other)
        self.assertEqual(Student.objects.get(user=self.student).enrollments.count(), 2)


# ---------------------------------------------------------------------------
# مدل‌ها و مشاوره
# ---------------------------------------------------------------------------

class ModelTests(LMSTestCase):
    def test_enrollment_can_cancel_rules(self):
        student, _ = Student.objects.get_or_create(user=self.student)
        enrollment = Enrollment.objects.create(student=student, course=self.course, status='approved')
        self.assertTrue(enrollment.can_cancel)            # بدون تاریخ شروع
        self.course.start_date = timezone.localdate() + timedelta(days=1)
        self.assertTrue(enrollment.can_cancel)            # فردا شروع می‌شود
        self.course.start_date = timezone.localdate()
        self.assertFalse(enrollment.can_cancel)           # امروز شروع شده
        enrollment.status = 'cancelled'
        self.assertFalse(enrollment.can_cancel)           # قبلاً لغو شده

    def test_unique_enrollment_constraint(self):
        from django.db import IntegrityError, transaction
        student, _ = Student.objects.get_or_create(user=self.student)
        Enrollment.objects.create(student=student, course=self.course)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Enrollment.objects.create(student=student, course=self.course)

    def test_course_capacity_properties(self):
        self.assertEqual(self.course.remaining_capacity, 2)
        self.enroll(self.student)
        self.assertEqual(self.course.remaining_capacity, 1)
        self.assertFalse(self.course.is_full)


@override_settings(KAVENEGAR_API_KEY='', ADMIN_PHONE_NUMBER='')
class ConsultationTests(TestCase):
    def test_consultation_request_is_saved(self):
        resp = self.client.post(
            reverse('courses:consultation_submit'),
            {'full_name': 'علی رضایی', 'phone': '09120000000', 'message': 'سلام'},
            HTTP_REFERER='/',
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(ConsultationRequest.objects.count(), 1)

    def test_invalid_consultation_not_saved(self):
        self.client.post(reverse('courses:consultation_submit'), {'full_name': '', 'phone': ''}, HTTP_REFERER='/')
        self.assertEqual(ConsultationRequest.objects.count(), 0)


class PublicPagesSmokeTests(LMSTestCase):
    def test_main_pages_render_for_anonymous(self):
        for name in ('home', 'courses:course_list', 'courses:instructor_list', 'login', 'accounts:signup'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, msg=name)
        self.assertEqual(
            self.client.get(reverse('courses:instructor_detail', args=[self.instructor.pk])).status_code, 200
        )

    def test_navbar_menu_depends_on_role(self):
        self.login(self.student)
        html = self.client.get(reverse('home')).content.decode()
        self.assertIn(reverse('courses:my_courses'), html)
        self.assertNotIn(reverse('courses:course_manage'), html)
        self.login(self.teacher)
        html = self.client.get(reverse('home')).content.decode()
        self.assertIn(reverse('courses:course_manage'), html)
        self.assertNotIn(reverse('accounts:user_list'), html)
        self.login(self.admin)
        html = self.client.get(reverse('home')).content.decode()
        self.assertIn(reverse('accounts:user_list'), html)
