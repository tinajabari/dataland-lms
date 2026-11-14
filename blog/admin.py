from django.contrib import admin
from .models import BlogPost

@admin.register(BlogPost)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'date_modified', 'date_created', 'author')
    ordering = ('-status',)


# admin.site.register(BlogPost, PostAdmin)

# Register your models here.
