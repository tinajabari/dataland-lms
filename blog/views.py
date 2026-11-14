import django.core.exceptions
from django.http import HttpResponse
from django.shortcuts import render
from .models import BlogPost
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404

from django.shortcuts import redirect

from django.contrib.auth.models import User
from .forms import NewPostForm

def post_list_view(request):
    # posts_list=BlogPost.objects.all()
    # posts_list = BlogPost.objects.filter(status='pub')
    posts_list = BlogPost.objects.filter(status='pub').order_by('-date_modified')

    return render(request, 'blog/post_list.html', {'posts_list': posts_list})

def post_detail_view(request, pk):
    postdetail = get_object_or_404(BlogPost, pk=pk)
    return render(request, 'blog/post_detail.html', {'post': postdetail})

def post_create_view(request):
    # print(request.method)
    # print('this is create view')
    # print(request.POST)
    # print(request.POST.get('title'))
    # print(request.POST.get('text'))

    # if request.method == 'POST':
    # print("Post Request")
    # print(request.POST.get('title'))
    # print(request.POST.get('text'))

    #     post_title = request.POST.get('title')
    #     post_text = request.POST.get('text')
    #
    #     user = User.objects.all()[0]
    #     BlogPost.objects.create(title=post_title, text=post_text, author=user, status='pub')
    #
    # else:
    #     print('Get Request')
    if request.method == 'POST':
        form = NewPostForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('post_list')
            # form = NewPostForm()

    else:
        form = NewPostForm()

    return render(request, 'blog/post_create.html', context={'form': form})

def post_update_view(request, pk):
    # post = BlogPost.objects.get(pk=pk)
    post = get_object_or_404(BlogPost, pk=pk)
    form = NewPostForm(request.POST or None, instance=post)
    if form.is_valid():
        form.save()
        return redirect('post_list')
    return render(request, 'blog/post_create.html', context={'form': form})

def post_delete_view(request, pk):
    post = get_object_or_404(BlogPost, pk=pk)
    if request.method == 'POST':
        post.delete()
        return redirect('post_list')
    return render(request, 'blog/post_delete.html', context={'post': post})