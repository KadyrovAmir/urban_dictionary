from django import forms
from django.contrib.auth.models import User
from website.models import CustomUser, Support


class EditUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name')


class EditProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ('description', 'photo')