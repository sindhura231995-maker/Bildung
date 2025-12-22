from django.db import models
from users.models import User
from django.conf import settings
from django.utils import timezone
import datetime
import uuid


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
    category = models.CharField(
        max_length=50, choices=CATEGORY_CHOICES, default='programming'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    structure_json = models.JSONField(default=dict)

    students = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="enrolled_courses", blank=True
    )

    def __str__(self):
        return self.title


class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True, related_name='modules')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.course.title} - {self.title}"

class CourseBlock(models.Model):
    BLOCK_TYPES = [
        ("Module", "Module"),
        ("Quiz", "Quiz"),
        ("Assignment", "Assignment"),
        ("Live Class", "Live Class"),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    type = models.CharField(max_length=50, choices=BLOCK_TYPES)
    title = models.CharField(max_length=255, blank=True)
    order = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.type} - {self.title or 'Untitled'}"
    
class Lecture(models.Model):
    module = models.ForeignKey(
        Module, on_delete=models.CASCADE, related_name="lectures"
    )
    title = models.CharField(max_length=255)
    video = models.FileField(upload_to="lectures/videos/", blank=True, null=True)
    file = models.FileField(upload_to="lectures/files/", blank=True, null=True)
    order = models.PositiveIntegerField(default=0)


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
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    reminder_sent = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.course.title} - {self.title} ({self.start_time})"


class Certificate(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    certificate_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    issued_on = models.DateField(auto_now_add=True)
    downloaded_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.student.username} - {self.course.title}"

    class Meta:
        unique_together = ('student', 'course')

class LiveClass(models.Model):
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='instructor_classes')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='live_classes')
    topic = models.CharField(max_length=255)
    meeting_link = models.URLField(max_length=500, blank=True, null=True)
    date = models.DateField()
    time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    reminder_sent = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    @property
    def start_datetime(self):
        dt = datetime.datetime.combine(self.date, self.time)
        return timezone.make_aware(dt)

    def __str__(self):
        return f"{self.topic} ({self.course.title}) on {self.date} at {self.time}"


class LectureQuestion(models.Model):
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, related_name="questions")
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student.username} - {self.question[:30]}"

class QuestionReply(models.Model):
    question = models.ForeignKey(LectureQuestion, on_delete=models.CASCADE, related_name="replies")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reply = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    upvotes = models.ManyToManyField(User, related_name="reply_upvotes", blank=True)

    def is_instructor(self):
        return self.user == self.question.lecture.module.course.instructor

    def likes(self):
        return self.upvotes.count()

    def __str__(self):
        return self.reply[:40]
    
    class Meta:
        ordering = ["-created_at"]


class CourseReview(models.Model):
    course = models.ForeignKey("courses.Course", on_delete=models.CASCADE, related_name="reviews")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="course_reviews")
    rating = models.IntegerField(default=5)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("course", "student")  

    def __str__(self):
        return f"{self.student} → {self.course} ({self.rating} stars)"
    
class LiveClassAttendance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    live_class = models.ForeignKey(LiveClass, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(default=0)  

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    message = models.CharField(max_length=255)
    url = models.CharField(max_length=255, blank=True, null=True)  # optional redirect
    created_at = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.message[:30]}"
    
class Assignment(models.Model):
    course = models.ForeignKey(Course, related_name="assignments", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.course.title} - Assignment: {self.title}"