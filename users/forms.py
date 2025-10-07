from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class StudentSignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = "student"
        if commit:
            user.save()
        return user


class InstructorSignUpForm(UserCreationForm):
    date_of_birth = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    gender = forms.ChoiceField(choices=User.GENDER_CHOICE)
    department = forms.CharField(max_length=100)
    position = forms.CharField(max_length=100)
    experience = forms.IntegerField(min_value=0)
    bio = forms.CharField(widget=forms.Textarea)

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'email',
            'password1',
            'password2',
            'date_of_birth',
            'gender',
            'department',
            'position',
            'experience',
            'bio',
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        # auto-fill username with email
        user.username = self.cleaned_data['email']
        if commit:
            user.save()
        return user
