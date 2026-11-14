from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from .forms import SignupForm, ProfileForm, UserAdminForm
from .roles import ADMIN, role_required, get_profile, get_role

User = get_user_model()


def signup_view(request):
    """ثبت‌نام کاربر جدید (دانشجو یا مدرس)."""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'ثبت‌نام با موفقیت انجام شد. خوش آمدی! 🎉')
            return redirect('home')
    else:
        form = SignupForm()
    return render(request, 'accounts/signup.html', {'form': form})


@login_required
def profile_view(request):
    """مشاهده و ویرایش اطلاعات کاربری خود کاربر."""
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'اطلاعات شما با موفقیت ذخیره شد.')
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=request.user)
    return render(request, 'accounts/profile.html', {
        'form': form,
        'profile': get_profile(request.user),
    })


@role_required(ADMIN)
def user_list_view(request):
    """فهرست کاربران برای مدیر (جستجو + فیلتر نقش + صفحه‌بندی)."""
    users = User.objects.select_related('profile').order_by('-date_joined')

    q = request.GET.get('q', '').strip()
    if q:
        users = users.filter(
            Q(username__icontains=q) | Q(first_name__icontains=q)
            | Q(last_name__icontains=q) | Q(email__icontains=q)
        )

    role = request.GET.get('role', '')
    if role in ('admin', 'instructor', 'student'):
        if role == 'admin':
            users = users.filter(Q(is_superuser=True) | Q(profile__role='admin'))
        else:
            users = users.filter(profile__role=role, is_superuser=False)

    page = Paginator(users, 15).get_page(request.GET.get('page'))
    # نقش هر کاربر برای نمایش (بدون ساخت پروفایل در حین نمایش لیست)
    for u in page:
        u.display_role = get_role(u)
    return render(request, 'accounts/user_list.html', {
        'page': page, 'q': q, 'selected_role': role,
    })


@role_required(ADMIN)
def user_update_view(request, pk):
    """ویرایش اطلاعات، نقش و وضعیت فعال بودن یک کاربر توسط مدیر."""
    target = get_object_or_404(User, pk=pk)
    editing_self = target.pk == request.user.pk

    if request.method == 'POST':
        form = UserAdminForm(request.POST, instance=target, editing_self=editing_self)
        if form.is_valid():
            form.save()
            messages.success(request, 'اطلاعات کاربر ذخیره شد.')
            return redirect('accounts:user_list')
    else:
        form = UserAdminForm(instance=target, editing_self=editing_self)
    return render(request, 'accounts/user_form.html', {
        'form': form, 'target': target, 'editing_self': editing_self,
    })


@role_required(ADMIN)
@require_POST
def user_toggle_active_view(request, pk):
    """فعال/غیرفعال کردن حساب کاربر (مدیر نمی‌تواند خودش را غیرفعال کند)."""
    target = get_object_or_404(User, pk=pk)
    if target.pk == request.user.pk:
        messages.error(request, 'نمی‌توانید حساب خودتان را غیرفعال کنید.')
    else:
        target.is_active = not target.is_active
        target.save(update_fields=['is_active'])
        state = 'فعال' if target.is_active else 'غیرفعال'
        messages.success(request, f'حساب «{target.username}» {state} شد.')
    return redirect('accounts:user_list')
