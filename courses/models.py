from django.db import models
from users.models import User
from django.conf import settings


class Course(models.Model):
    CATEGORY_CHOICES = [
        ('business', 'Business'),
        ('design', 'Design'),
        ('music', 'Music'),
        ('programming', 'Programming'),
        ('others', 'Others'),
    ]

    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="courses"
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    # Keep the new category field
    category = models.CharField(
        max_length=50, choices=CATEGORY_CHOICES, default='programming'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    # students enrolled
    students = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="enrolled_courses", blank=True
    )

    def __str__(self):
        return self.title


class Module(models.Model):
    course = models.ForeignKey(
        Course, related_name='modules', on_delete=models.CASCADE
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class Lecture(models.Model):
    module = models.ForeignKey(
        Module, on_delete=models.CASCADE, related_name="lectures"
    )
    title = models.CharField(max_length=255)
    video = models.FileField(upload_to="lectures/videos/", blank=True, null=True)
    file = models.FileField(upload_to="lectures/files/", blank=True, null=True)

    def __str__(self):
        return f"{self.module.title} - {self.title}"


class Enrollment(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, related_name="enrollments", on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'course')  

    def __str__(self):
        return f"{self.student.username} -> {self.course.title}"


class Feedback(models.Model):
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="feedbacks"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_feedbacks"
    )
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="instructor_feedbacks"
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback from {self.instructor.username} to {self.student.username} ({self.course.title})"

    
class LectureProgress(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, limit_choices_to={'role': 'student'})
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, related_name="lecture_progress")
    progress = models.FloatField(default=0.0)
    duration = models.FloatField(default=0.0)
    completed = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
    last_position = models.FloatField(default=0.0)

    class Meta:
        unique_together = ('student', 'lecture')

    def __str__(self):
        return f"{self.student.username} - {self.lecture.title} ({'Done' if self.completed else 'Pending'})"



class CourseEvent(models.Model):
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="events"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date = models.DateField(null=True, blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.course.title} - {self.title} ({self.start_time})"


import uuid

class Certificate(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    certificate_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    issued_on = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.course.title}"

    class Meta:
        unique_together = ('student', 'course')

        
class LiveClass(models.Model):
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='instructor_classes')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='live_classes')
    topic = models.CharField(max_length=255)
    date = models.DateField()
    time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.topic} ({self.course.title}) on {self.date} at {self.time}"
