from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Profile, InstructorProfile
from django.contrib.auth import get_user_model

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

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = "instructor"
        user.username = self.cleaned_data["email"]  # Email is used as username
        if commit:
            user.save()
        return user 


User = get_user_model()

class ProfileForm(forms.ModelForm):
    resume = forms.FileField(
        required=False, 
        help_text="Only PDF files are allowed.", 
        label="Resume (PDF Only)",
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Profile
        fields = ['about_me', 'phone', 'gender', 'date_of_birth', 'qualification', 'resume']
        widgets = {
            'about_me': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'qualification': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_resume(self):
        resume = self.cleaned_data.get('resume')

        if resume:
            if not resume.name.lower().endswith('.pdf'):
                raise forms.ValidationError("Only PDF files are allowed for the resume.")

        return resume

class UserDisplayForm(forms.ModelForm):

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
        }

User = get_user_model()
class InstructorUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

class InstructorUserReadOnlyForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'readonly': True}),
        }

class InstructorProfileForm(forms.ModelForm):

    resume = forms.FileField(
        required=False,
        help_text="Upload only PDF.",
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = InstructorProfile
        fields = [
            'professional_title',
            'expertise',
            'experience',
            'about_me',
            'phone',
            'gender',
            'date_of_birth',
            'qualification',
            'resume'
        ]

        widgets = {
            'professional_title': forms.TextInput(attrs={'class': 'form-control'}),
            'expertise': forms.TextInput(attrs={'class': 'form-control'}),
            'experience': forms.NumberInput(attrs={'class': 'form-control'}),
            'about_me': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'qualification': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_resume(self):
        resume = self.cleaned_data.get("resume")
        if resume and not resume.name.lower().endswith(".pdf"):
            raise forms.ValidationError("Only PDF files are allowed.")
        return resume
