from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from courses.models import Course, Instructor, Student
from .roles import ADMIN, INSTRUCTOR, STUDENT, can_manage_course, get_role, set_role

User = get_user_model()
PW = 'Str0ng-Pass!23'


def make_user(username, role=STUDENT, **extra):
    user = User.objects.create_user(username, password=PW, **extra)
    set_role(user, role)
    return user


class RoleTests(TestCase):
    def test_new_user_gets_student_profile(self):
        user = User.objects.create_user('u1', password=PW)
        self.assertEqual(user.profile.role, STUDENT)
        self.assertEqual(get_role(user), STUDENT)

    def test_superuser_is_admin(self):
        root = User.objects.create_superuser('root', 'root@example.com', PW)
        self.assertEqual(get_role(root), ADMIN)

    def test_set_role_instructor_creates_instructor_profile(self):
        user = make_user('t1', INSTRUCTOR)
        self.assertEqual(get_role(user), INSTRUCTOR)
        self.assertTrue(Instructor.objects.filter(user=user).exists())

    def test_set_role_student_creates_student_profile(self):
        user = make_user('s1', STUDENT)
        self.assertTrue(Student.objects.filter(user=user).exists())

    def test_admin_role_grants_and_revokes_staff_access(self):
        user = make_user('a1', ADMIN)
        self.assertTrue(user.is_staff and user.is_superuser)
        set_role(user, STUDENT)
        self.assertFalse(user.is_staff or user.is_superuser)
        self.assertEqual(get_role(user), STUDENT)

    def test_can_manage_course(self):
        admin = make_user('a1', ADMIN)
        owner = make_user('t1', INSTRUCTOR)
        other = make_user('t2', INSTRUCTOR)
        student = make_user('s1', STUDENT)
        course = Course.objects.create(
            title='c', slug='c', description='d', instructor=Instructor.objects.get(user=owner)
        )
        self.assertTrue(can_manage_course(admin, course))
        self.assertTrue(can_manage_course(owner, course))
        self.assertFalse(can_manage_course(other, course))
        self.assertFalse(can_manage_course(student, course))


class SignupTests(TestCase):
    def data(self, **overrides):
        data = {
            'username': 'newuser', 'first_name': 'علی', 'last_name': 'رضایی',
            'email': 'ali@example.com', 'role': 'student', 'phone': '09120000000',
            'password1': PW, 'password2': PW,
        }
        data.update(overrides)
        return data

    def test_signup_page_renders(self):
        self.assertEqual(self.client.get(reverse('accounts:signup')).status_code, 200)

    def test_signup_as_student(self):
        resp = self.client.post(reverse('accounts:signup'), self.data())
        self.assertRedirects(resp, reverse('home'))
        user = User.objects.get(username='newuser')
        self.assertEqual(get_role(user), STUDENT)
        self.assertEqual(user.profile.phone, '09120000000')
        self.assertTrue(Student.objects.filter(user=user).exists())
        self.assertIn('_auth_user_id', self.client.session)  # بعد از ثبت‌نام لاگین شده

    def test_signup_as_instructor(self):
        self.client.post(reverse('accounts:signup'), self.data(username='teach', role='instructor'))
        user = User.objects.get(username='teach')
        self.assertEqual(get_role(user), INSTRUCTOR)
        self.assertTrue(Instructor.objects.filter(user=user).exists())

    def test_cannot_self_signup_as_admin(self):
        resp = self.client.post(reverse('accounts:signup'), self.data(username='hacker', role='admin'))
        self.assertEqual(resp.status_code, 200)  # فرم با خطا برگشت
        self.assertFalse(User.objects.filter(username='hacker').exists())

    def test_password_mismatch_rejected(self):
        resp = self.client.post(reverse('accounts:signup'), self.data(password2='different-pass-1'))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(username='newuser').exists())


class LoginLogoutTests(TestCase):
    def test_login_and_logout(self):
        make_user('stu', STUDENT)
        resp = self.client.post(reverse('login'), {'username': 'stu', 'password': PW})
        self.assertRedirects(resp, reverse('home'))
        self.assertIn('_auth_user_id', self.client.session)
        self.client.post(reverse('logout'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_wrong_password(self):
        make_user('stu', STUDENT)
        resp = self.client.post(reverse('login'), {'username': 'stu', 'password': 'wrong'})
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)


class UserManagementPermissionTests(TestCase):
    def setUp(self):
        self.admin = make_user('admin1', ADMIN)
        self.teacher = make_user('teacher1', INSTRUCTOR)
        self.student = make_user('student1', STUDENT)

    def test_user_list_access_by_role(self):
        url = reverse('accounts:user_list')
        self.assertEqual(self.client.get(url).status_code, 302)  # مهمان → صفحه ورود
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_admin_changes_role(self):
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse('accounts:user_update', args=[self.student.pk]),
            {'first_name': 'نرگس', 'last_name': 'رضایی', 'email': 's@example.com',
             'is_active': 'on', 'role': 'instructor', 'phone': ''},
        )
        self.assertRedirects(resp, reverse('accounts:user_list'))
        self.assertEqual(get_role(User.objects.get(pk=self.student.pk)), INSTRUCTOR)

    def test_non_admin_cannot_edit_users(self):
        self.client.force_login(self.teacher)
        resp = self.client.post(
            reverse('accounts:user_update', args=[self.student.pk]),
            {'first_name': 'x', 'last_name': 'y', 'email': '', 'is_active': 'on',
             'role': 'admin', 'phone': ''},
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(get_role(User.objects.get(pk=self.student.pk)), STUDENT)

    def test_admin_toggles_other_user_active(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('accounts:user_toggle_active', args=[self.student.pk]))
        self.assertFalse(User.objects.get(pk=self.student.pk).is_active)

    def test_admin_cannot_deactivate_self(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('accounts:user_toggle_active', args=[self.admin.pk]))
        self.assertTrue(User.objects.get(pk=self.admin.pk).is_active)

    def test_non_admin_cannot_toggle_active(self):
        self.client.force_login(self.teacher)
        resp = self.client.post(reverse('accounts:user_toggle_active', args=[self.student.pk]))
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(User.objects.get(pk=self.student.pk).is_active)


class ProfileTests(TestCase):
    def test_profile_requires_login(self):
        self.assertEqual(self.client.get(reverse('accounts:profile')).status_code, 302)

    def test_user_updates_own_profile(self):
        user = make_user('stu', STUDENT)
        self.client.force_login(user)
        resp = self.client.post(reverse('accounts:profile'), {
            'first_name': 'مینا', 'last_name': 'صادقی',
            'email': 'mina@example.com', 'phone': '09350000000',
        })
        self.assertRedirects(resp, reverse('accounts:profile'))
        fresh = User.objects.get(pk=user.pk)
        self.assertEqual(fresh.first_name, 'مینا')
        self.assertEqual(fresh.profile.phone, '09350000000')
