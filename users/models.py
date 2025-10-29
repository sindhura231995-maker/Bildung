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

    # Additional fields
    date_of_birth = models.DateField(null=True, blank=True)
    GENDER_CHOICE = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    POSITION_CHOICES = (
        ('professor', 'Professor'),
        ('associate', 'Associate Professor'),
        ('assistant', 'Assistant Professor'),
        ('lecturer', 'Lecturer'),
    )


    EXPERIENCE_CHOICES = (
        ('0-1', '0-1 years'),
        ('1-2', '1-2 years'),
        ('2-3', '2-3 years'),
        ('3+', '3+ years'),
    )
    

    gender = models.CharField(max_length=1, choices=GENDER_CHOICE, null=True, blank=True)
    department = models.CharField(max_length=100, blank=True)
    position = models.CharField(max_length=50, choices=POSITION_CHOICES, null=True, blank=True)
    experience = models.CharField(max_length=20, choices=EXPERIENCE_CHOICES, null=True, blank=True)
    bio = models.TextField(blank=True)

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