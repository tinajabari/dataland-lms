from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Profile
from .roles import get_profile, set_role, ADMIN, INSTRUCTOR, STUDENT

User = get_user_model()


class BootstrapFormMixin:
    """به همه فیلدهای فرم کلاس‌های بوت‌استرپ می‌دهد."""

    def apply_bootstrap(self):
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css = 'form-check-input'
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                css = 'form-select'
            else:
                css = 'form-control'
            existing = widget.attrs.get('class', '')
            if css not in existing:
                widget.attrs['class'] = f'{existing} {css}'.strip()


class SignupForm(BootstrapFormMixin, UserCreationForm):
    """ثبت‌نام کاربر جدید. مدیر فقط از پنل ادمین/مدیریت کاربران ساخته می‌شود."""
    SELF_SIGNUP_ROLES = [
        (STUDENT, 'دانشجو'),
        (INSTRUCTOR, 'مدرس'),
    ]

    role = forms.ChoiceField(
        choices=SELF_SIGNUP_ROLES, initial=STUDENT, label='نقش من'
    )
    phone = forms.CharField(max_length=20, required=False, label='شماره تماس')

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')
        labels = {
            'username': 'نام کاربری',
            'first_name': 'نام',
            'last_name': 'نام خانوادگی',
            'email': 'ایمیل',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].label = 'رمز عبور'
        self.fields['password2'].label = 'تکرار رمز عبور'
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True
        self.apply_bootstrap()

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            profile = set_role(user, self.cleaned_data['role'])
            profile.phone = self.cleaned_data.get('phone', '')
            profile.save(update_fields=['phone'])
        return user


class ProfileForm(BootstrapFormMixin, forms.ModelForm):
    """ویرایش اطلاعات کاربری توسط خود کاربر."""
    phone = forms.CharField(max_length=20, required=False, label='شماره تماس')

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')
        labels = {
            'first_name': 'نام',
            'last_name': 'نام خانوادگی',
            'email': 'ایمیل',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        profile = get_profile(self.instance)
        if profile is not None:
            self.fields['phone'].initial = profile.phone
        self.apply_bootstrap()

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            profile = get_profile(user)
            profile.phone = self.cleaned_data.get('phone', '')
            profile.save(update_fields=['phone'])
        return user


class UserAdminForm(BootstrapFormMixin, forms.ModelForm):
    """ویرایش کاربر توسط مدیر (شامل نقش و فعال/غیرفعال بودن)."""
    role = forms.ChoiceField(choices=Profile.ROLE_CHOICES, label='نقش')
    phone = forms.CharField(max_length=20, required=False, label='شماره تماس')

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'is_active')
        labels = {
            'first_name': 'نام',
            'last_name': 'نام خانوادگی',
            'email': 'ایمیل',
            'is_active': 'حساب فعال است',
        }

    def __init__(self, *args, editing_self=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.editing_self = editing_self
        profile = get_profile(self.instance)
        self.fields['role'].initial = profile.role
        self.fields['phone'].initial = profile.phone
        if editing_self:
            # مدیر نباید بتواند نقش یا فعال بودن حساب خودش را خراب کند
            self.fields['role'].disabled = True
            self.fields['is_active'].disabled = True
        self.apply_bootstrap()

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            profile = get_profile(user)
            profile.phone = self.cleaned_data.get('phone', '')
            profile.save(update_fields=['phone'])
            if not self.editing_self and self.cleaned_data['role'] != profile.role:
                set_role(user, self.cleaned_data['role'])
        return user
