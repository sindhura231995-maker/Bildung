import datetime
from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from courses.models import LiveClass, CourseEvent, Enrollment
from courses.models import Notification

def check_and_send_reminders(user):

    if not user.is_authenticated:
        return

    now = timezone.now()
    reminder_delta = timedelta(minutes=30)
    reminder_cutoff = now + reminder_delta

    #  STUDENT REMINDERS

    if hasattr(user, "role") and user.role == "student":

        enrollments = Enrollment.objects.filter(student=user).select_related("course")

        for enr in enrollments:
            course = enr.course

            for cls in course.live_classes.filter(reminder_sent=False):
                start_dt = timezone.make_aware(
                    datetime.datetime.combine(cls.date, cls.time)
                )

                if now < start_dt <= reminder_cutoff:
                    Notification.objects.create(
                        user=user,
                        message=f"Reminder: Live class '{cls.topic}' starts in 30 minutes.",
                        url=reverse("student:student_upcoming_classes")

                    )
                    cls.reminder_sent = True
                    cls.save(update_fields=["reminder_sent"])

            for event in course.events.filter(
                start_time__gt=now,
                start_time__lte=reminder_cutoff, 
                reminder_sent=False,
            ):
                Notification.objects.create(
                    user=user,
                    message=f"Reminder: Event '{event.title}' starts in 30 minutes.",
                    url=reverse("student:student_upcoming_classes")

                )
                event.reminder_sent = True
                event.save(update_fields=["reminder_sent"])

    #  INSTRUCTOR REMINDERS

    if hasattr(user, "role") and user.role == "instructor":

        live_classes = LiveClass.objects.filter(
            instructor=user,
            reminder_sent=False
        )

        for cls in live_classes:
            start_dt = timezone.make_aware(
                datetime.datetime.combine(cls.date, cls.time)
            )

            if now < start_dt <= reminder_cutoff:
                Notification.objects.create(
                    user=user,
                    message=f"Reminder: Your live class '{cls.topic}' starts in 30 minutes.",
                    url=reverse("instructor:calendar_view")

                )
                cls.reminder_sent = True
                cls.save(update_fields=["reminder_sent"])

        events = CourseEvent.objects.filter(
            course__instructor=user,
            reminder_sent=False,
            start_time__gt=now,
            start_time__lte=reminder_cutoff,  
        )

        for event in events:
            Notification.objects.create(
                user=user,
                message=f"Reminder: Your event '{event.title}' starts in 30 minutes.",
                url=reverse("instructor:calendar_view")

            )
            event.reminder_sent = True
            event.save(update_fields=["reminder_sent"])

