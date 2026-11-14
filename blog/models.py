from django.db import models

# Create your models here.

class BlogPost(models.Model):

    def __str__(self):
        return self.title

    STATUS_CHOICES =(
    ('pub', 'Published'),
    ('drf', 'Draft'),
    )


    title = models.CharField(max_length=100)
    text = models.TextField()
    author = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    status = models.CharField(choices=STATUS_CHOICES, max_length=3)