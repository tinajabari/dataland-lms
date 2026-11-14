from django.contrib import admin
from .models import Instructor, Category, Course, Student, Enrollment, ConsultationRequest, Lesson


@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = ('user', 'specialty', 'phone')
    search_fields = ('user__first_name', 'user__last_name', 'specialty')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    fields = ('order', 'title', 'content_url')
    ordering = ('order',)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    inlines = [LessonInline]
    list_display = ('title', 'instructor', 'category', 'level', 'price', 'is_active', 'remaining_capacity')
    list_filter = ('level', 'is_active', 'category')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'national_code')
    search_fields = ('user__first_name', 'user__last_name', 'national_code')


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'status', 'registered_at', 'score')
    list_filter = ('status', 'course')
    actions = ['approve_enrollments']

    def approve_enrollments(self, request, queryset):
        queryset.update(status='approved')
    approve_enrollments.short_description = 'تایید ثبت‌نام‌های انتخاب‌شده'


@admin.register(ConsultationRequest)
class ConsultationRequestAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'created_at', 'is_read')
    list_filter = ('is_read',)
    search_fields = ('full_name', 'phone', 'message')
    ordering = ('-created_at',)
    actions = ['mark_as_read']

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = 'علامت‌گذاری به‌عنوان خوانده‌شده'


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order', 'created_at')
    list_filter = ('course',)
    search_fields = ('title', 'description', 'content')
    ordering = ('course', 'order')
