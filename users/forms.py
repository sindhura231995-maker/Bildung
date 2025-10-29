from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class StudentSignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["first_name","last_name", "email", "password1", "password2"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"]  # Email is used as username
        if commit:
            user.save()
        return user 

class InstructorSignUpForm(UserCreationForm):
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}), required=True
    )
    gender = forms.ChoiceField(choices=User.GENDER_CHOICE, required=True)
    department = forms.CharField(max_length=100, required=True)
    position = forms.ChoiceField(choices=User.POSITION_CHOICES, required=True)
    experience = forms.ChoiceField(choices=User.EXPERIENCE_CHOICES, required=True)
    bio = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
            "date_of_birth",
            "gender",
            "department",
            "position",
            "experience",
            "bio",
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = "instructor"
        user.username = self.cleaned_data["email"]  # Email is used as username
        if commit:
            user.save()
        return user 