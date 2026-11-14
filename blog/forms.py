from django import forms
from django.forms import ModelForm

from .models import BlogPost

class NewPostForm(ModelForm):
     class Meta:
         model=BlogPost
         fields=['title','text','author','status']
         widgets = {
             'title': forms.TextInput(attrs={'class': 'form-control'}),
             'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
             'author': forms.Select(attrs={'class': 'form-select'}),
             'status': forms.Select(attrs={'class': 'form-select'}),
         }