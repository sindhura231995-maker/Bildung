from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings


class User(AbstractUser):
    
    # Roles: student, instructor, admin
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('instructor', 'Instructor'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')

    # Using email as unique identifier
    email = models.EmailField(unique=True)


    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    def __str__(self):
        return f"{self.email} ({self.role})"


"""
class Course(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'is_instructor': True}  # if you have role flags
    )
    students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='enrolled_courses',
        blank=True,
        limit_choices_to={'is_student': True}
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
"""

def user_resume_path(instance, filename):
    # File will be uploaded to: resumes/user_<id>/<filename>
    return f'resumes/user_{instance.user.id}/{filename}'

def user_profile_image_path(instance, filename):
    # File will be uploaded to: profile_images/user_<id>/<filename>
    return f'profile_images/user_{instance.user.id}/{filename}'



from django.contrib.auth import get_user_model
    # Get the custom or default User model
User = get_user_model()

class Profile(models.Model):
    """
    Holds supplementary profile information for a User.
    """
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    
    # 🌟 Core Link: Ensures every User has exactly one Profile (and vice-versa).
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE
    )
    
    # Personal Fields
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
    
    # File Upload Field (Requires Pillow to be installed: pip install Pillow)
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
