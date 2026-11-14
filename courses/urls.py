from django.urls import path

from . import views

app_name = 'courses'

# نکته: مسیرهای ثابت (manage, new, my-courses, ...) باید قبل از مسیرهای <slug> بیایند
# و در RESERVED_SLUGS (courses/forms.py) هم ثبت شده باشند تا با slug دوره‌ها تداخل نکنند.
urlpatterns = [
    # دوره‌ها
    path('', views.course_list_view, name='course_list'),
    path('manage/', views.manage_courses_view, name='course_manage'),
    path('new/', views.course_create_view, name='course_create'),
    path('my-courses/', views.my_courses_view, name='my_courses'),
    path('consultation/', views.consultation_submit_view, name='consultation_submit'),

    # اساتید
    path('instructors/', views.instructor_list_view, name='instructor_list'),
    path('instructors/<int:pk>/', views.instructor_detail_view, name='instructor_detail'),

    # درس‌ها
    path('lessons/<int:pk>/', views.lesson_detail_view, name='lesson_detail'),
    path('lessons/<int:pk>/edit/', views.lesson_update_view, name='lesson_update'),
    path('lessons/<int:pk>/delete/', views.lesson_delete_view, name='lesson_delete'),

    # ثبت‌نام
    path('enrollments/<int:pk>/cancel/', views.enrollment_cancel_view, name='enrollment_cancel'),

    # جزئیات و مدیریت یک دوره (با slug)
    path('<str:slug>/', views.course_detail_view, name='course_detail'),
    path('<str:slug>/edit/', views.course_update_view, name='course_update'),
    path('<str:slug>/delete/', views.course_delete_view, name='course_delete'),
    path('<str:slug>/toggle-active/', views.course_toggle_active_view, name='course_toggle_active'),
    path('<str:slug>/students/', views.course_students_view, name='course_students'),
    path('<str:slug>/enroll/', views.enroll_course_view, name='enroll_course'),
    path('<str:slug>/lessons/new/', views.lesson_create_view, name='lesson_create'),
]
