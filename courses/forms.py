from django import forms
from .models import ConsultationRequest


class ConsultationForm(forms.ModelForm):
    class Meta:
        model = ConsultationRequest
        fields = ['full_name', 'phone', 'message']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'مثلاً تینا جباری '
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': '09xxxxxxxxx'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'سوال یا نیازت رو بنویس (اختیاری)'
            }),
        }
        labels = {
            'full_name': 'نام و نام خانوادگی',
            'phone': 'شماره تماس',
            'message': 'پیام',
        }


# ---------------------------------------------------------------------------
# فرم‌های مدیریت دوره و درس (LMS)
# ---------------------------------------------------------------------------
from django.utils.text import slugify

from accounts.forms import BootstrapFormMixin
from .models import Course, Lesson

# آدرس‌هایی که نباید به‌عنوان slug دوره استفاده شوند (با مسیرهای ثابت تداخل دارند)
RESERVED_SLUGS = {
    'my-courses', 'manage', 'new', 'consultation',
    'instructors', 'lessons', 'enrollments',
}


class CourseForm(BootstrapFormMixin, forms.ModelForm):
    """
    ایجاد/ویرایش دوره.
    - مدیر می‌تواند «مدرس دوره» را انتخاب کند (اختصاص مدرس به دوره).
    - مدرس عادی این فیلد را نمی‌بیند و دوره به‌طور خودکار به خودش اختصاص می‌یابد.
    - اگر slug خالی بماند، از روی عنوان ساخته می‌شود.
    """

    class Meta:
        model = Course
        fields = [
            'title', 'slug', 'instructor', 'category', 'level',
            'short_description', 'description', 'price', 'capacity',
            'cover_image', 'start_date', 'end_date', 'is_active',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 6}),
            'short_description': forms.TextInput(),
            'start_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'end_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }
        labels = {
            'slug': 'آدرس دوره (slug)',
            'category': 'دسته‌بندی',
            'level': 'سطح دوره',
            'start_date': 'تاریخ شروع',
            'end_date': 'تاریخ پایان',
            'cover_image': 'تصویر دوره',
        }
        help_texts = {
            'slug': 'بخشی از آدرس دوره. اگر خالی بگذارید از روی عنوان ساخته می‌شود.',
        }

    def __init__(self, *args, can_choose_instructor=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['slug'].required = False
        self.fields['instructor'].required = True
        if not can_choose_instructor:
            del self.fields['instructor']
        self.apply_bootstrap()

    def clean(self):
        cleaned = super().clean()
        title = cleaned.get('title')
        slug = (cleaned.get('slug') or '').strip()

        if slug:
            if slug in RESERVED_SLUGS:
                self.add_error('slug', 'این آدرس رزرو شده است؛ آدرس دیگری انتخاب کنید.')
        elif title:
            # slug حداکثر ۵۰ کاراکتر است؛ برای عنوان‌های طولانی کوتاهش می‌کنیم
            base = (slugify(title, allow_unicode=True)[:40].strip('-')) or 'course'
            slug = base
            others = Course.objects.exclude(pk=self.instance.pk)
            counter = 2
            while slug in RESERVED_SLUGS or others.filter(slug=slug).exists():
                slug = f'{base}-{counter}'
                counter += 1
        cleaned['slug'] = slug

        start, end = cleaned.get('start_date'), cleaned.get('end_date')
        if start and end and end < start:
            self.add_error('end_date', 'تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد.')
        return cleaned

    def clean_capacity(self):
        capacity = self.cleaned_data['capacity']
        if capacity < 1:
            raise forms.ValidationError('ظرفیت باید حداقل ۱ نفر باشد.')
        return capacity


class LessonForm(BootstrapFormMixin, forms.ModelForm):
    """ایجاد/ویرایش درس یک دوره."""

    class Meta:
        model = Lesson
        fields = ['title', 'description', 'content', 'content_url', 'order']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'content': forms.Textarea(attrs={'rows': 8}),
            'content_url': forms.URLInput(attrs={'placeholder': 'https://...'}),
            'order': forms.NumberInput(attrs={'min': 1}),
        }
        help_texts = {
            'order': 'درس‌ها بر اساس این عدد (کوچک‌تر = اول) مرتب می‌شوند.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()

    def clean(self):
        cleaned = super().clean()
        if not (cleaned.get('content') or cleaned.get('content_url')):
            raise forms.ValidationError(
                'حداقل یکی از «محتوای آموزشی (متن)» یا «آدرس محتوا» را وارد کنید.'
            )
        return cleaned
