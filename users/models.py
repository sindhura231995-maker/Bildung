from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone


class User(AbstractUser):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('instructor', 'Instructor'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    email = models.EmailField(unique=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    def __str__(self):
        return f"{self.email} ({self.role})"


def user_resume_path(instance, filename):
    return f'resumes/user_{instance.user.id}/{filename}'

def user_profile_image_path(instance, filename):
    return f'profile_images/user_{instance.user.id}/{filename}'


User = get_user_model()
class Profile(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE
    )
    profile_picture = models.ImageField(upload_to="student_profiles/", blank=True, null=True)
    about_me = models.TextField(
        blank=True, 
        null=True
    )
    
    phone = models.CharField(
        max_length=15, 
        blank=True, 
        null=True
    )
    
    gender = models.CharField(
        max_length=1, 
        choices=GENDER_CHOICES, 
        blank=True, 
        null=True
    )
    
    date_of_birth = models.DateField(
        blank=True, 
        null=True
    )
    
    qualification = models.CharField(
        max_length=100, 
        blank=True, 
        null=True
    )
    
    resume = models.FileField(
        upload_to='resumes/', 
        blank=True, 
        null=True,
        help_text="Upload a PDF file for your resume."
    )
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"{self.user.username}'s Profile"


class InstructorProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="instructor_profile"
    )
    profile_picture = models.ImageField(upload_to="instructor_profiles/", blank=True, null=True)
    professional_title = models.CharField(max_length=200, blank=True, null=True)
    expertise = models.CharField(max_length=200, blank=True, null=True)
    experience = models.PositiveIntegerField(blank=True, null=True)

    about_me = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    gender = models.CharField(
        max_length=10,
        choices=[("male", "Male"), ("female", "Female"), ("other", "Other")],
        blank=True, null=True
    )
    date_of_birth = models.DateField(blank=True, null=True)
    qualification = models.CharField(max_length=120, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Instructor Profile — {self.user.username}"

    
class LoginHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    login_time = models.DateTimeField(default=timezone.now)
    logout_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default="Success")
    device = models.CharField(max_length=255, default="Unknown")

    def date(self):
        return self.login_time.date()

    def time(self):
        return self.login_time.time()
