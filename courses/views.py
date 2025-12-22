from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.utils.dateparse import parse_datetime, parse_date, parse_time
from django.views.decorators.csrf import csrf_exempt

from courses.utils import check_and_send_reminders
from quizzes.models import Quiz, QuizResult
from .models import Assignment, Course, CourseBlock, Enrollment, Lecture, LectureProgress, Feedback, CourseEvent, Module, Certificate,LiveClass, LectureQuestion, QuestionReply, CourseReview, LiveClassAttendance, Notification
from users.models import InstructorProfile, LoginHistory, User
from .forms import CourseForm, LectureForm, FeedbackForm, ModuleFormSet, LiveClassForm, CourseReviewForm, CourseEventForm
from io import BytesIO
from users.decorators import instructor_required
from django.db.models import Q, Count, Sum
from users.models import Profile
from datetime import date, datetime
from django.utils import timezone

from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from django.http import FileResponse, HttpResponse, HttpResponseForbidden
import json
from django.contrib.auth import update_session_auth_hash


# -------------------------------
# Common Views
# -------------------------------


def course_list(request):
    query = request.GET.get('q')
    courses = Course.objects.all()

    if query:
        courses = courses.filter(
            Q(title__icontains=query)
        )

    return render(request, 'courses/course_list.html', {'courses': courses, 'query': query})

@login_required(login_url='/login/')
def browse_courses(request):
    """Student: browse unenrolled courses"""
    if getattr(request.user, 'role', None) != 'student':
        return redirect('login')

    available_courses = Course.objects.exclude(students=request.user)
    return render(request, 'courses/student/browse_course.html', {'courses': available_courses})


# -------------------------------
# Student Views
# -------------------------------


@login_required(login_url='/login/')
def enroll_course(request, course_id):
    if getattr(request.user, 'role', None) != 'student':
        return redirect('student_login')
    course = get_object_or_404(Course, id=course_id)
    Enrollment.objects.get_or_create(student=request.user, course=course)
    
    Notification.objects.create(
        user=request.user,
        message=f"You have successfully enrolled in {course.title}.",
        url=f"/student/course/{course.id}/"
    )

    messages.success(request, f"Enrolled in {course.title}")
    return redirect('student:my_courses')

@login_required
def my_courses(request):
    enrolled_courses = Enrollment.objects.filter(student=request.user).select_related('course')
    return render(request, "courses/student/my_courses.html", {
        "enrolled_courses": enrolled_courses
    })

@login_required(login_url="/student/login/")
def student_course_detail(request, course_id):

    enrollment = get_object_or_404(
        Enrollment,
        course_id=course_id,
        student=request.user
    )
    course = enrollment.course

    structure = course.structure_json or []

    modules_map = {
        m.id: m for m in
        course.modules.prefetch_related("lectures").all()
    }
    quizzes_map = {q.id: q for q in course.quizzes.all()}
    assignments_map = {a.id: a for a in course.assignments.all()}
    lectures = Lecture.objects.filter(module__course=course)
    total = lectures.count()

    completed_lectures = set(
        LectureProgress.objects.filter(
            student=request.user,
            lecture__in=lectures,
            completed=True
        ).values_list("lecture_id", flat=True)
    )

    completed = len(completed_lectures)
    progress_percent = int((completed / total * 100) if total else 0)
    unlocked_modules = []
    all_previous_complete = True

    for module in modules_map.values():
        if all_previous_complete:
            unlocked_modules.append(module.id)

        module_lectures = module.lectures.all()
        if not all(l.id in completed_lectures for l in module_lectures):
            all_previous_complete = False

    ordered_items = []
    module_count = 1
    quiz_count = 1
    assignment_count = 1

    for item in structure:
        item_type = item.get("type")

        if item_type == "Module":
            module = modules_map.get(item.get("module_id"))
            if module:
                ordered_items.append({
                    "type": "module",
                    "title": f"Module {module_count}",
                    "obj": module
                })
                module_count += 1

        elif item_type == "Quiz":
            quiz = quizzes_map.get(item.get("quiz_id"))
            if quiz:
                ordered_items.append({
                    "type": "quiz",
                    "title": f"Quiz {quiz_count}",
                    "obj": quiz
                })
                quiz_count += 1

        elif item_type == "Assignment":
            assignment = assignments_map.get(item.get("assignment_id"))
            if assignment:
                ordered_items.append({
                    "type": "assignment",
                    "title": f"Assignment {assignment_count}",
                    "obj": assignment
                })
                assignment_count += 1

    try:
        user_review = CourseReview.objects.get(
            course=course,
            student=request.user
        )
    except CourseReview.DoesNotExist:
        user_review = None

    return render(
        request,
        "courses/student_course_detail.html",
        {
            "course": course,
            "ordered_items": ordered_items,
            "progress_map": completed_lectures,
            "completed": completed,
            "total": total,
            "progress_percent": progress_percent,
            "unlocked_modules": unlocked_modules,
            "user_review": user_review,
        }
    )

@login_required
def view_student_profile(request, student_id):
    
    student_profile = get_object_or_404(Profile, user__id=student_id)

    context = {
        'profile': student_profile,   
        'is_instructor_view': True,   
    }
    return render(request, 'student/student_profile.html', context)

@login_required(login_url='/login/')
def mark_lecture_complete(request, lecture_id):
    """Student: mark lecture complete"""
    lecture = get_object_or_404(Lecture, id=lecture_id)

    course = lecture.module.course

    if getattr(request.user, 'role', None) != 'student':
        return redirect('login')

    LectureProgress.objects.update_or_create(
        student=request.user,
        lecture=lecture,
        defaults={'completed': True}
    )

    return redirect('student:student_course_detail', course_id=lecture.module.course.id)
from django.http import JsonResponse

@login_required(login_url='/student/login/')
def auto_mark_complete(request, lecture_id):
    """Auto-mark lecture complete when video ends and update progress bar."""
    if request.method == "POST":
        lecture = get_object_or_404(Lecture, id=lecture_id)
        course = lecture.module.course

        watched_time = float(request.POST.get("watched_time", 0))
        duration = float(request.POST.get("duration", 0))

        progress, created = LectureProgress.objects.update_or_create(
            student=request.user,
            lecture=lecture,
            defaults={
                "completed": True,
                "last_position": duration  
            }
        )

        total_lectures = Lecture.objects.filter(module__course=course).count()
        completed_lectures = LectureProgress.objects.filter(
            student=request.user,
            lecture__module__course=course,
            completed=True
        ).count()
        progress_percent = int((completed_lectures / total_lectures) * 100) if total_lectures > 0 else 0

        return JsonResponse({
            "status": "success",
            "message": "Lecture marked complete.",
            "completed": completed_lectures,
            "total": total_lectures,
            "progress_percent": progress_percent
        })

    return JsonResponse({"status": "error", "message": "Invalid request."}, status=400)


@login_required(login_url='/login/')
def undo_lecture_completion(request, lecture_id):
    """Student: undo completed lecture"""
    lecture = get_object_or_404(Lecture, id=lecture_id)
    course = lecture.module.course

    if getattr(request.user, 'role', None) != 'student':
        return redirect('login')

    progress = LectureProgress.objects.filter(student=request.user, lecture=lecture).first()
    if progress:
        progress.delete()

    return redirect('student:student_course_detail', course_id=course.id)



@login_required(login_url='/student/login/')
def student_progress(request, course_id):
    """
    Student: View overall progress for a course (without individual lectures)
    """
    enrollment = get_object_or_404(Enrollment, course_id=course_id, student=request.user)
    course = enrollment.course

    lectures = Lecture.objects.filter(module__course=course)
    total = lectures.count()

    completed = LectureProgress.objects.filter(
        student=request.user,
        lecture__in=lectures,
        completed=True
    ).count() if total > 0 else 0

    progress_percent = int((completed / total * 100) if total else 0)

    context = {
        'course': course,
        'total': total,
        'completed': completed,
        'progress_percent': progress_percent,
    }

    return render(request, 'courses/student/student_course_progress.html', context)


@login_required
def get_certificate(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    lectures = Lecture.objects.filter(module__course=course)
    total = lectures.count()
    completed = LectureProgress.objects.filter(student=user, lecture__in=lectures, completed=True).count()

    if total == 0 or completed < total:
        messages.warning(request, "You must complete all lectures to get your certificate.")
        return redirect('student:student_course_detail', course_id)

    certificate, created = Certificate.objects.get_or_create(student=user, course=course)

    certificate.downloaded_at = timezone.now()
    certificate.save()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    p.setFont("Helvetica-Bold", 28)
    p.drawCentredString(width/2, height - 150, "Certificate of Completion")

    p.setFont("Helvetica", 16)
    p.drawCentredString(width/2, height - 200, "This is to certify that")

    p.setFont("Helvetica-Bold", 20)
    full_name = f"{user.first_name} {user.last_name}".strip() or user.username
    p.drawCentredString(width/2, height - 250, full_name)

    p.setFont("Helvetica", 16)
    p.drawCentredString(width/2, height - 300, "has successfully completed the course")

    p.setFont("Helvetica-Bold", 20)
    p.drawCentredString(width/2, height - 340, course.title)

    p.setFont("Helvetica", 12)
    p.drawCentredString(width/2, height - 400, f"Issued on: {certificate.issued_on.strftime('%B %d, %Y')}")
    p.drawCentredString(width/2, height - 420, f"Certificate ID: {certificate.certificate_id}")

    p.line(150, height - 500, width - 150, height - 500)
    p.setFont("Helvetica-Oblique", 12)
    p.drawCentredString(width/2, height - 520, "Bildung Learning Platform")

    p.showPage()
    p.save()
    buffer.seek(0)

    return FileResponse(buffer, as_attachment=True, filename=f"{course.title}_Certificate.pdf")


@login_required
def my_certificates(request):
    certs = Certificate.objects.filter(student=request.user)
    return render(request, 'courses/student/my_certificates.html', {'certificates': certs})

@login_required(login_url='/login/')
def student_upcoming_classes(request):
    user = request.user

    enrolled_course_ids = Enrollment.objects.filter(
        student=user
    ).values_list('course_id', flat=True)

    upcoming_classes = LiveClass.objects.filter(
        course_id__in=enrolled_course_ids,
        date__gte=date.today()
    ).select_related('course', 'instructor').order_by('date', 'time')

    upcoming_events = CourseEvent.objects.filter(
        course_id__in=enrolled_course_ids,
        start_time__gte=timezone.now()
    ).select_related('course').order_by('start_time')

    events = []

    for cls in upcoming_classes:
        events.append({
            "id": cls.id,
            "type": "live_class",
            "title": cls.topic,
            "topic": cls.topic,
            "course_name": cls.course.title,
            "instructor": cls.instructor.get_full_name() or cls.instructor.username,
            "start": f"{cls.date}T{cls.time}",
            "join_link": cls.meeting_link or "",
            "classNames": ["live-class-event"],   
        })

    for ev in upcoming_events:
        events.append({
            "id": ev.id,
            "type": "event",
            "title": ev.title,
            "topic": ev.title,                       
            "event_title": ev.title,
            "event_description": ev.description,
            "course_name": ev.course.title,
            "start": ev.start_time.isoformat(),
            "end": ev.end_time.isoformat(),
            "event_link": "",                         
            "classNames": ["event-class"],            
        })

    return render(request, 'courses/student/student_calendar.html', {
        'events_json': json.dumps(events)
    })


@login_required
def account_settings(request):
    if request.user.role != "student":
        return redirect("login")
    
    user = request.user
    profile, created = Profile.objects.get_or_create(user=user)
    
    if request.method == 'POST':

        if 'update_profile' in request.POST:
            
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)
            user.email = request.POST.get('email', user.email)
            user.save()

            profile.phone = request.POST.get('phone', profile.phone)
            profile.about_me = request.POST.get('about_me', profile.about_me)
            profile.gender = request.POST.get('gender', profile.gender)
            profile.qualification = request.POST.get('qualification', profile.qualification)

            dob = request.POST.get('date_of_birth')
            if dob:
                profile.date_of_birth = dob

            if 'resume' in request.FILES:
                profile.resume = request.FILES['resume']

            if 'profile_picture' in request.FILES:
                profile.profile_picture = request.FILES['profile_picture']

            profile.save()

            messages.success(request, "Profile updated successfully!")
            return redirect('student:account_settings')

        elif 'change_password' in request.POST:

            old_password = request.POST.get('old_password')
            new_password1 = request.POST.get('new_password1')
            new_password2 = request.POST.get('new_password2')
            
            if user.check_password(old_password):
                if new_password1 == new_password2:
                    if len(new_password1) >= 8:
                        user.set_password(new_password1)
                        user.save()
                        update_session_auth_hash(request, user)
                        messages.success(request, "Password changed successfully!")
                    else:
                        messages.error(request, "Password must be at least 8 characters long.")
                else:
                    messages.error(request, "New passwords do not match.")
            else:
                messages.error(request, "Current password is incorrect.")

            return redirect('student:account_settings')

        elif 'update_notifications' in request.POST:
            email_notifications = 'email_notifications' in request.POST
            course_updates = 'course_updates' in request.POST

            messages.success(request, "Notification preferences updated!")
            return redirect('student:account_settings')
    
    context = {
        'user': user,
        'profile': profile,
    }
    return render(request, 'courses/student/account_settings.html', context)


@login_required
def student_my_activity(request):
    user = request.user
    enrollments = Enrollment.objects.filter(student=user)

    course_progress = []
    for enroll in enrollments:
        course = enroll.course
        lectures = Lecture.objects.filter(module__course=course)
        total_lectures = lectures.count()

        completed = LectureProgress.objects.filter(
            student=user, lecture__in=lectures, completed=True
        ).count()

        percent = round((completed / total_lectures) * 100, 2) if total_lectures > 0 else 0

        course_progress.append({
            "course": course,
            "total_lectures": total_lectures,
            "completed_lectures": completed,
            "progress_percent": percent,
        })

    recent_videos = LectureProgress.objects.filter(
        student=user, completed=True
    ).select_related("lecture", "lecture__module__course").order_by("-updated_at")[:10]

    video_lessons_watched = LectureProgress.objects.filter(
        student=user, completed=True
    ).select_related("lecture", "lecture__module__course").order_by("-updated_at")

    enrolled_course_ids = enrollments.values_list("course_id", flat=True)

    all_live_classes = LiveClass.objects.filter(course_id__in=enrolled_course_ids)

    total_classes = all_live_classes.count()

    attendance_records = (
        LiveClassAttendance.objects
        .filter(user=user, live_class__in=all_live_classes)
        .select_related("live_class", "live_class__course")
    )

    attended_count = attendance_records.exclude(joined_at=None).count()

    attendance_percent = round((attended_count / total_classes) * 100, 2) if total_classes > 0 else 0

    attendance_data = {
        "total_classes": total_classes,
        "classes_attended": attended_count,
        "attendance_percentage": attendance_percent,
        "absences": total_classes - attended_count,
        "live_classes": [
            {
                "title": rec.live_class.title,
                "course": rec.live_class.course.title,
                "date": rec.live_class.date,
                "status": "Joined" if rec.joined_at else "Missed",
                "joined_at": rec.joined_at,
                "duration": f"{rec.duration} mins" if rec.duration else "—",
            }
            for rec in attendance_records
        ]
    }

    login_history = LoginHistory.objects.filter(user=user).order_by("-login_time")[:25]

    qna_activity = (
        LectureQuestion.objects.filter(student=user)
        .select_related("lecture", "lecture__module", "lecture__module__course")
        .prefetch_related("replies__user")
        .order_by("-created_at")
    )

    total_completed = LectureProgress.objects.filter(student=user, completed=True).count()
    total_lectures = Lecture.objects.count()
    overall_progress = (
        round((total_completed / total_lectures) * 100, 2) if total_lectures > 0 else 0
    )

    context = {
        "total_enrolled_courses": enrollments.count(),
        "total_completed_lectures": total_completed,
        "overall_progress": overall_progress,
        "course_progress": course_progress,
        "recent_videos": recent_videos,
        "video_lessons_watched": video_lessons_watched,
        "attendance_data": attendance_data,
        "login_history": login_history,
        "qna_activity": qna_activity,
    }

    return render(request, "courses/student/my_activity.html", context)
    

@login_required
def ask_question(request, lecture_id):
    lecture = get_object_or_404(Lecture, id=lecture_id)
    course = lecture.module.course

    if request.method == "POST":
        question_text = request.POST.get("question")

        if question_text:
            LectureQuestion.objects.create(
                lecture=lecture,
                student=request.user,
                question=question_text
            )

            Notification.objects.create(
                user=course.instructor,
                message=f"{request.user.username} asked a question in {course.title}",
                url=reverse("instructor:course_overview", args=[course.id]) + "?tab=questions"
            )

        return redirect("student:course_qna", course_id=course.id)

    
@login_required
def edit_question(request, question_id):
    question = get_object_or_404(LectureQuestion, id=question_id, student=request.user)

    if request.method == "POST":
        question.question = request.POST.get("question")
        question.save()
        return redirect("student:course_qna", course_id=question.lecture.module.course.id)

    return render(request, "courses/student/edit_question.html", {
        "question": question
    })

    
@login_required
def delete_question(request, question_id):
    question = get_object_or_404(LectureQuestion, id=question_id, student=request.user)
    course_id = question.lecture.module.course.id
    question.delete()
    return redirect("student:course_qna", course_id=course_id)

@login_required
def course_qna(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    sort = request.GET.get("sort", "recent")

    questions = LectureQuestion.objects.filter(
        lecture__module__course=course
    ).order_by("-created_at")
    my_questions = questions.filter(student=request.user)
    my_replies = QuestionReply.objects.filter(
        question__lecture__module__course=course,
        user=request.user
    ).order_by("-created_at")

    if sort == "liked":
        questions = questions.annotate(
            top_likes=Count("replies__upvotes")
        ).order_by("-top_likes", "-created_at")

    return render(request, "courses/student/student_QandA.html", {
        "course": course,
        "questions": questions,
        "my_questions": my_questions,
        "my_replies": my_replies,
        "sort": sort,
    })


@login_required
def upvote_reply(request, reply_id):
    reply = get_object_or_404(QuestionReply, id=reply_id)

    if request.user in reply.upvotes.all():
        reply.upvotes.remove(request.user)
    else:
        reply.upvotes.add(request.user)

    return redirect("student:course_qna", course_id=reply.question.lecture.module.course.id)

@login_required
def leave_review(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    try:
        review = CourseReview.objects.get(course=course, student=request.user)
        is_update = True
    except CourseReview.DoesNotExist:
        review = None
        is_update = False

    if request.method == "POST":
        form = CourseReviewForm(request.POST, instance=review)

        if form.is_valid():
            review_obj = form.save(commit=False)
            review_obj.course = course
            review_obj.student = request.user
            review_obj.save()

            Notification.objects.create(
                user=course.instructor,
                message=f"{request.user.username} left a review for {course.title}",
                url=reverse("instructor:course_overview", args=[course.id]) + "?tab=reviews"
            )
            if is_update:
                messages.success(request, "Your review has been updated.")
            else:
                messages.success(request, "Thank you! Your review has been submitted.")

            return redirect("student:student_course_detail", course_id=course.id)

    return redirect("student:course_detail", course_id=course.id)


@login_required
def student_notifications(request):
    notifications = Notification.objects.filter(user=request.user).order_by("-created_at")

    return render(request, "courses/student/student_notifications.html", {
        "notifications": notifications
    })


@login_required
def get_recent_notifications(request):
    notes = Notification.objects.filter(user=request.user).order_by("-created_at")[:10]

    data = []
    for n in notes:
        data.append({
            "id": n.id,
            "message": n.message,
            "url": n.url or "",
            "is_read": n.is_read,
            "created_at": n.created_at.strftime("%d %b %Y, %I:%M %p")
        })

    unread = Notification.objects.filter(user=request.user, is_read=False).count()

    return JsonResponse({"notifications": data, "unread": unread})


@login_required
def mark_notifications_read(request, notif_id):
    Notification.objects.filter(id=notif_id, user=request.user).update(is_read=True)
    return JsonResponse({"status": "ok"})

@login_required
def mark_notification_read(request, notif_id):
    """Mark a single notification as read."""
    Notification.objects.filter(id=notif_id, user=request.user).update(is_read=True)
    return JsonResponse({"status": "ok"})

# -------------------------------
# Instructor Views
# -------------------------------

@login_required
def instructor_dashboard(request):
    check_and_send_reminders(request.user)
    courses = Course.objects.filter(instructor=request.user)
    unread_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()

    total_students = Enrollment.objects.filter(
        course__in=courses
    ).values('student').distinct().count()

    return render(request, 'courses/instructor/instructor_dashboard.html', {
        'courses': courses,
        'total_students': total_students,
        "unread_count": unread_count,
    })

"""
@login_required
def course_edit(request, course_id):
    course = get_object_or_404(Course, id=course_id, instructor=request.user)
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, "Course updated successfully.")
            return redirect('instructor:instructor_dashboard')
    else:
        form = CourseForm(instance=course)
    return render(request, 'courses/instructor/course_edit.html', {'form': form, 'course': course})


@login_required
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id, instructor=request.user)
    modules = course.modules.all()
    lectures = []
    for module in course.modules.all():
        lectures = module.lectures.all()

    return render(request, 'courses/instructor/course_detail.html', {
        'course': course,
        'modules': modules,
        'lectures': lectures,
        'quizzes': course.quizzes.all(),        
        'assignments': course.assignments.all(),
        'live_classes': course.live_classes.all() 
    })

"""

@login_required
def course_detail(request, course_id):
    course = get_object_or_404(
        Course, id=course_id, instructor=request.user
    )

    ordered_items = []
    structure = course.structure_json or []

    module_count = 1
    quiz_count = 1
    assignment_count = 1
    live_count = 1

    for item in structure:
        item_type = item.get("type")
        module_id = item.get("module_id")
        display_title = item.get("display_title", "").strip()

        if item_type == "Module" and module_id:
            module = course.modules.filter(id=module_id).first()
            if module:
                title = display_title or f"Module {module_count}"
                ordered_items.append({
                    "type": "module",
                    "obj": module,
                    "title": title
                })
                module_count += 1

        elif item_type == "Quiz":
            quiz = course.quizzes.first()
            if quiz:
                title = display_title or f"Quiz {quiz_count}"
                ordered_items.append({
                    "type": "quiz",
                    "obj": quiz,
                    "title": title
                })
                quiz_count += 1

        elif item_type == "Assignment":
            assignment = course.assignments.first()
            if assignment:
                title = display_title or f"Assignment {assignment_count}"
                ordered_items.append({
                    "type": "assignment",
                    "obj": assignment,
                    "title": title
                })
                assignment_count += 1

        elif item_type == "LiveClass":
            live = course.live_classes.first()
            if live:
                title = display_title or f"Live Class {live_count}"
                ordered_items.append({
                    "type": "live",
                    "obj": live,
                    "title": title
                })
                live_count += 1

    return render(
        request,
        "courses/instructor/course_detail.html",
        {
            "course": course,
            "ordered_items": ordered_items,
        },
    )


@login_required
def add_lecture(request, course_id):
    course = get_object_or_404(Course, id=course_id, instructor=request.user)
    if request.method == 'POST':
        form = LectureForm(request.POST, request.FILES)
        if form.is_valid():
            lecture = form.save(commit=False)
            lecture.course = course
            lecture.save()
            messages.success(request, "Lecture added successfully.")
            return redirect('instructor:course_detail', course_id=course.id)
    else:
        form = LectureForm()
    return render(request, 'courses/instructor/add_lecture.html', {'form': form, 'course': course})


@login_required
def edit_lecture(request, course_id, lecture_id):
    lecture = get_object_or_404(Lecture, id=lecture_id, course_id=course_id, course_instructor=request.user)
    if request.method == "POST":
        form = LectureForm(request.POST, request.FILES, instance=lecture)
        if form.is_valid():
            form.save()
            messages.success(request, "Lecture updated successfully.")
            return redirect('instructor:course_detail', course_id=course_id)
    else:
        form = LectureForm(instance=lecture)
    return render(request, 'courses/instructor/edit_lecture.html', {'form': form, 'course_id': course_id})


@login_required
def delete_lecture(request, course_id, lecture_id):
    lecture = get_object_or_404(Lecture, id=lecture_id, course_id=course_id, course_instructor=request.user)
    if request.method == "POST":
        lecture.delete()
        messages.success(request, "Lecture deleted successfully.")
        return redirect('instructor:course_detail', course_id=course_id)
    return render(request, 'courses/instructor/delete_lecture.html', {'lecture': lecture, 'course_id': course_id})


@login_required
def course_progress_report(request, course_id):
    course = get_object_or_404(Course, id=course_id, instructor=request.user)
    enrollments = Enrollment.objects.filter(course=course)
    progress_data = []
    total_lectures = sum(module.lectures.count() for module in course.modules.all())

    for enrollment in enrollments:
        student = enrollment.student
        completed = LectureProgress.objects.filter(
            student=student,
            lecture__module__course=course,  
            completed=True
        ).count()
        progress = (completed / total_lectures * 100) if total_lectures else 0
        progress_data.append({
            "student": student,
            "completed": completed,
            "total": total_lectures,
            "progress": progress
        })

    return render(request, 'courses/instructor/course_progress_report.html', {
        'course': course,
        'progress_data': progress_data
    })

@login_required
def add_event(request):

    instructor = request.user
    instructor_courses = Course.objects.filter(instructor=instructor)

    if request.method == "POST":
        form = CourseEventForm(request.POST)

        selected_course_id = request.POST.get("course")  

        if not selected_course_id:
            messages.error(request, "Please select a course.")
            return redirect("instructor:add_event")

        course = get_object_or_404(Course, id=selected_course_id, instructor=instructor)

        if form.is_valid():
            event = form.save(commit=False)
            event.course = course
            event.save()

            students = Enrollment.objects.filter(course=course).values_list("student_id", flat=True)
            for student_id in students:
                Notification.objects.create(
                    user_id=student_id,
                    message=f"New Event: {event.title} ({course.title})",
                    url=reverse("student:student_upcoming_classes")

                )

            messages.success(request, "Event created successfully!")
            return redirect("instructor:calendar_view")

    else:
        form = CourseEventForm()

    return render(request, "courses/instructor/add_event.html", {
        "form": form,
        "instructor_courses": instructor_courses,
        "selected_course_id": None,
    })

@login_required
def edit_event(request, event_id):
    event = get_object_or_404(CourseEvent, id=event_id, course__instructor=request.user)

    if request.method == "POST":
        event.title = request.POST.get("title")
        event.description = request.POST.get("description")
        event.start_time = request.POST.get("start_time")
        event.end_time = request.POST.get("end_time")
        event.save()
        messages.success(request, "Event updated successfully!")
        return redirect("instructor:calendar_view")

    return render(request, "courses/instructor/edit_event.html", {
        "event": event
    })

@login_required
def delete_event(request, event_id):
    event = get_object_or_404(CourseEvent, id=event_id, course__instructor=request.user)
    event.delete()
    messages.success(request, "Event deleted.")
    return redirect("instructor:calendar_view")

@login_required
def give_feedback(request, course_id):
    course = get_object_or_404(Course, id=course_id, instructor=request.user)

    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.instructor = request.user
            feedback.course = course
            feedback.save()
            messages.success(request, "Feedback submitted successfully!")
            return redirect('instructor:course_detail', course_id=course.id)
    else:
        form = FeedbackForm()
       
    return render(request, 'courses/instructor/give_feedback.html', {'form': form, 'course': course})

@login_required(login_url='/login/')
def student_course_list(request):
    """Student: list all available courses (both enrolled and unenrolled)"""
    if getattr(request.user, 'role', None) != 'student':
        return redirect('login')

    courses = Course.objects.all()
    enrolled_ids = Enrollment.objects.filter(student=request.user).values_list('course_id', flat=True)

    for course in courses:
        course.is_enrolled = course.id in enrolled_ids

    return render(request, 'courses/student/student_course_list.html', {'courses': courses})


@login_required
def my_students(request):

    enrollments = Enrollment.objects.filter(course__instructor=request.user).select_related('student', 'course')
    students = {}
    
    for enrollment in enrollments:
        student = enrollment.student
        course = enrollment.course
        lectures = Lecture.objects.filter(module__course=course)
        total_lectures = lectures.count()
        completed = LectureProgress.objects.filter(
            student=student, lecture__in=lectures, completed=True
        ).count()
        
        percent = int((completed / total_lectures) * 100) if total_lectures else 0
        
        if student.id not in students:
            students[student.id] = {
                'student': student,
                'courses': []
            }
        students[student.id]['courses'].append({
            'title': course.title,
            'progress': percent
        })
    
    return render(request, 'courses/instructor/my_students.html', {
        'students_data': students.values(),  
    })

@login_required
def students_list(request):
    instructor = request.user
    query = request.GET.get("q", "").strip()
    instructor_courses = Course.objects.filter(instructor=instructor)

    enrollments = Enrollment.objects.filter(
        course__in=instructor_courses
    ).select_related("student", "course")

    if query:
        enrollments = enrollments.filter(
            Q(student__first_name__icontains=query) |
            Q(student__last_name__icontains=query) |
            Q(student__username__icontains=query) |
            Q(student__email__icontains=query)
        )

    students_map = {}

    for e in enrollments:
        student = e.student

        if student.id not in students_map:
            last_login_obj = LoginHistory.objects.filter(
                user=student
            ).order_by("-login_time").first()

            students_map[student.id] = {
                "student": student,
                "courses": [],
                "completed_courses": 0,
                "last_login": last_login_obj.login_time if last_login_obj else None,
                "total_progress": 0,
                "course_count": 0,
            }

        course = e.course
        lectures = Lecture.objects.filter(module__course=course)
        total_lectures = lectures.count()
        completed_lectures = LectureProgress.objects.filter(
            student=student,
            lecture__in=lectures,
            completed=True
        ).count()

        progress = round((completed_lectures / total_lectures) * 100) if total_lectures else 0

        students_map[student.id]["courses"].append({
            "course": course,
            "course_id": course.id,
            "title": course.title,
            "progress": progress,
        })

        students_map[student.id]["total_progress"] += progress
        students_map[student.id]["course_count"] += 1

        if progress == 100:
            students_map[student.id]["completed_courses"] += 1

    students_data = []
    for s in students_map.values():
        if s["course_count"]:
            avg = s["total_progress"] / s["course_count"]
        else:
            avg = 0
        s["average_progress"] = round(avg)
        students_data.append(s)

    total_courses = instructor_courses.count()

    if students_data:
        overall_avg_progress = round(
            sum(s["average_progress"] for s in students_data) / len(students_data)
        )
    else:
        overall_avg_progress = 0

    total_assignments = 0  

    context = {
        "students_data": students_data,
        "query": query,
        "total_courses": total_courses,
        "average_progress": overall_avg_progress,
        "total_assignments": total_assignments,
    }

    return render(request, "courses/instructor/students_list.html", context)



@login_required
def add_course(request):
    course_id = request.GET.get("course_id")

    if course_id:
        course = get_object_or_404(Course, id=course_id, instructor=request.user)

        return render(request, "courses/instructor/add_course.html", {
            "course_id": course.id,
            "preload": json.dumps(course.structure_json or []),
            "course_title": course.title,
            "course_description": course.description,
            "course_price": course.price,
            "course_category": course.category,
        })

    return render(request, "courses/instructor/add_course.html", {
        "course_id": "null",
        "preload": json.dumps([]),
        "course_title": "",
        "course_description": "",
        "course_price": "",
        "course_category": "",
    })


@csrf_exempt
@login_required
def create_module(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    data = json.loads(request.body or "{}")
    course_id = data.get("course_id")

    if not course_id:
        return JsonResponse({"error": "course_id missing"}, status=400)

    course = get_object_or_404(Course, id=course_id, instructor=request.user)

    module = Module.objects.create(
        course=course,
        title="",
        description=""
    )

    return JsonResponse({"module_id": module.id})


@csrf_exempt
@login_required
def save_module(request, module_id):

    module = get_object_or_404(Module, id=module_id, course__instructor=request.user)
    course = module.course

    title = request.POST.get("module_title", "").strip()
    description = request.POST.get("description", "")

    if not title:
        structure = course.structure_json or []
        index = 1

        for i, item in enumerate(structure):
            if item.get("module_id") == module_id:
                index = i + 1
                break

        title = f"Module {index}"

    module.title = title
    module.description = description
    module.save()

    module.lectures.all().delete()

    lecture_count = int(request.POST.get("lecture_count", 0))

    for i in range(lecture_count):

        lec_title = request.POST.get(f"lecture_title_{i}", "")
        video = request.FILES.get(f"lecture_video_{i}")
        pdf = request.FILES.get(f"lecture_pdf_{i}")

        Lecture.objects.create(
            module=module,
            title=lec_title,
            video=video,
            file=pdf,
            order=i
        )

    return JsonResponse({"status": "success"})


@csrf_exempt
@login_required
def save_course(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    data = json.loads(request.body)

    course_id = data.get("course_id")
    structure = data.get("structure", [])

    if course_id:
        course = get_object_or_404(Course, id=course_id, instructor=request.user)
        course.title = data["title"]
        course.description = data["description"]
        course.price = data["price"]
        course.category = data["category"]
        course.structure_json = structure
        course.save()

        course.quizzes.all().delete()
        course.assignments.all().delete()
        course.live_classes.all().delete()

    else:
        course = Course.objects.create(
            instructor=request.user,
            title=data["title"],
            description=data["description"],
            price=data["price"],
            category=data["category"],
            structure_json=structure,
        )

    updated_structure = []

    for index, item in enumerate(structure):

        if item["type"] == "Module":
            if item.get("module_id"):  
                module = Module.objects.get(id=item["module_id"])
                module.order = index
                module.save()
            else:
                module = Module.objects.create(
                    course=course,
                    title=item.get("title", "Module"),
                    order=index
                )
                item["module_id"] = module.id

        elif item["type"] == "Quiz":
            q = Quiz.objects.create(
                course=course,
                title=item.get("title", "Quiz"),
                order=index
            )
            item["quiz_id"] = q.id

        elif item["type"] == "Assignment":
            a = Assignment.objects.create(
                course=course,
                title=item.get("title", "Assignment"),
                order=index
            )
            item["assignment_id"] = a.id

        elif item["type"] == "Live Class":
            lc = LiveClass.objects.create(
                course=course,
                instructor=request.user,
                topic=item.get("title", "Live Class"),
                order=index
            )
            item["liveclass_id"] = lc.id

        updated_structure.append(item)

    course.structure_json = updated_structure
    course.save()

    return JsonResponse({
        "status": "success",
        "course_id": course.id,
        "structure": updated_structure
    })

@csrf_exempt
@login_required
def delete_module(request, module_id):

    module = get_object_or_404(Module, id=module_id, course__instructor=request.user)
    course = module.course

    module.delete()  

    updated = []
    for item in course.structure_json:
        if item.get("module_id") != module_id:
            updated.append(item)

    for i, item in enumerate(updated):
        item["order"] = i

    course.structure_json = updated
    course.save()

    return JsonResponse({
        "status": "success",
        "message": "Module deleted",
        "structure": updated
    })


@login_required
def edit_module(request, course_id, module_id):
    module = get_object_or_404(Module, id=module_id, course_id=course_id)

    lectures = module.lectures.all().order_by("id")

    return render(request, "courses/instructor/edit_module.html", {
        "module": module,
        "lectures": lectures,
        "course_id": course_id
    })


@login_required
def add_module(request, course_id, module_id):

    course = get_object_or_404(Course, id=course_id, instructor=request.user)
    module = get_object_or_404(Module, id=module_id, course=course)
    structure = course.structure_json or []
    order_index = 1

    for i, item in enumerate(structure):
        if item.get("module_id") == module_id:
            order_index = i + 1 
            break

    return render(request, "courses/instructor/add_module.html", {
        "course_id": course_id,
        "module": module,
        "order_index": order_index,
        "lectures": module.lectures.all(),
    })


@login_required
def save_quiz(request, module_id):
    course = get_object_or_404(course,)
    Quiz.title = request.POST.get("module_title")
    Module.description = request.POST.get("module_description")
    Module.save()
    return JsonResponse({"status": "saved"})

@login_required
def add_lecture(request, module_id):
    module = get_object_or_404(Module, id=module_id)

    title = request.POST.get("title")
    video = request.FILES.get("video")
    pdf = request.FILES.get("pdf")

    lec = Lecture.objects.create(
        module=module,
        title=title,
        video=video,
        file=pdf
    )

    return JsonResponse({
        "status": "added",
        "lecture_id": lec.id,
        "title": lec.title
    })


@login_required
def delete_lecture(request, lecture_id):
    l = get_object_or_404(Lecture, id=lecture_id)
    l.delete()
    return JsonResponse({"status": "deleted"})


@login_required
def publish_course(request, course_id):

    course = get_object_or_404(Course, id=course_id, instructor=request.user)

    messages.success(request, f"Course '{course.title}' published successfully!")

    return redirect("instructor:instructor_dashboard")


def edit_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    blocks = CourseBlock.objects.filter(course=course).order_by("order")

    return render(request, "courses/instructor/edit_course.html", {
        "course": course,
        "blocks": blocks,
    })

@login_required(login_url='/login/')
def schedule_live_class(request):
    instructor = request.user

    courses = Course.objects.filter(instructor=instructor)

    if request.method == 'POST':
        form = LiveClassForm(request.POST)

        if form.is_valid():
            live_class = form.save(commit=False)
            live_class.instructor = instructor
            live_class.course = form.cleaned_data["course"]  
            live_class.meeting_link = form.cleaned_data.get("meeting_link")
            live_class.reminder_sent = False  
            live_class.save()

            students = Enrollment.objects.filter(
                course=live_class.course
            ).values_list("student_id", flat=True)

            for student_id in students:
                Notification.objects.create(
                    user_id=student_id,
                    message=f"New live class scheduled: {live_class.topic} ({live_class.course.title})",
                    url=reverse("student:student_upcoming_classes")
                )

            messages.success(request, 
                f"✅ Live class '{live_class.topic}' scheduled successfully!"
            )

            return redirect('instructor:calendar_view')

    else:
        form = LiveClassForm()

    return render(request, 'courses/instructor/schedule_live_class.html', {
        'form': form,
        'courses': courses,
    })

@login_required
def edit_live_class(request, class_id):
    liveclass = get_object_or_404(LiveClass, id=class_id, instructor=request.user)

    if request.method == "POST":
        topic = request.POST.get("topic")
        date = request.POST.get("date")
        time = request.POST.get("time")
        meeting_link = request.POST.get("meeting_link")

        liveclass.topic = topic
        liveclass.date = date
        liveclass.time = time
        liveclass.meeting_link = meeting_link
        liveclass.save()
        students = Enrollment.objects.filter(
                course=liveclass.course
            ).values_list("student_id", flat=True)

        for student_id in students:
                Notification.objects.create(
                    user_id=student_id,
                    message=f"Your live class schedule was modified: {liveclass.topic} ({liveclass.course.title})",
                    url=reverse("student:student_upcoming_classes")
                )


        messages.success(request, "Class updated successfully.")
        return redirect("instructor:calendar_view")

    return render(request, "courses/instructor/edit_live_class.html", {
        "liveclass": liveclass
    })

@login_required
def delete_live_class(request, class_id):
    live_class = get_object_or_404(LiveClass, id=class_id, course__instructor=request.user)
    live_class.delete()
    messages.success(request, "Live class deleted.")
    return redirect("instructor:calendar_view")


@login_required(login_url='/login/')
def my_activity(request):
    live_classes = LiveClass.objects.filter(instructor=request.user).order_by('-date', '-time')
    return render(request, 'courses/instructor/my_activity.html', {'live_classes': live_classes})


@login_required
def calendar_view(request):
    instructor = request.user
    live_classes = LiveClass.objects.filter(
        course__instructor=instructor,
        date__gte=date.today()
    ).select_related("course")

    events_qs = CourseEvent.objects.filter(
        course__instructor=instructor,
        start_time__gte=timezone.now()
    ).select_related("course")

    calendar_events = []

    for cls in live_classes:
        calendar_events.append({
            "id": cls.id,
            "type": "live_class",
            "title": cls.topic,
            "topic": cls.topic,
            "course_name": cls.course.title,
            "start": f"{cls.date}T{cls.time}",
            "join_link": cls.meeting_link or "",
            "course_id": cls.course.id,
            "backgroundColor": "#0d6efd",
            "borderColor": "#0d6efd",
        })

    for ev in events_qs:
        calendar_events.append({
            "id": ev.id,
            "type": "event",
            "title": ev.title,
            "event_title": ev.title,
            "event_description": ev.description,
            "course_name": ev.course.title,
            "start": ev.start_time.isoformat(),
            "end": ev.end_time.isoformat(),
            "course_id": ev.course.id,
            "event_link": "",  # if needed
            "backgroundColor": "#198754",
            "borderColor": "#198754",
        })

    return render(request, "courses/instructor/instructor_schedule.html", {
        "events": json.dumps(calendar_events),
        "live_classes": live_classes,
        "events_list": events_qs,
    })


@login_required
def instructor_qna(request, course_id):
    course = get_object_or_404(Course, id=course_id, instructor=request.user)

    questions = LectureQuestion.objects.filter(
        lecture__module__course=course
    ).order_by("-created_at")

    return render(request, "courses/instructor/instructor_qna.html", {
        "course": course,
        "questions": questions
    })

@login_required
def add_reply(request, question_id):
    question = get_object_or_404(LectureQuestion, id=question_id)

    if request.method == "POST":
        reply_text = request.POST.get("reply")

        if reply_text:
            reply_obj = QuestionReply.objects.create(
                question=question,
                user=request.user,
                reply=reply_text
            )

            Notification.objects.create(
                user=question.student, 
                message=f"Instructor replied to your question in {question.lecture.module.course.title}",
                url=reverse(
                    "student:course_qna",
                    args=[question.lecture.module.course.id]
                ) + "?highlight=" + str(reply_obj.id)
            )

    return redirect(
        "instructor:course_overview",
        course_id=question.lecture.module.course.id
    )


@login_required
def edit_reply(request, reply_id):
    reply = get_object_or_404(QuestionReply, id=reply_id)

    if reply.user != request.user:
        return HttpResponseForbidden("You cannot edit this reply")

    if request.method == "POST":
        reply.reply = request.POST.get("reply")
        reply.save()
        return redirect("instructor:course_overview", course_id=reply.question.lecture.module.course.id)

    return render(request, "courses/instructor/edit_reply.html", {"reply": reply})


@login_required
def delete_reply(request, reply_id):
    reply = get_object_or_404(QuestionReply, id=reply_id)

    if reply.user != request.user:
        return HttpResponseForbidden("You cannot delete this reply")

    course_id = reply.question.lecture.module.course.id
    reply.delete()

    return redirect("instructor:course_overview", course_id=course_id)

@login_required
def course_overview(request, course_id):
    course = get_object_or_404(Course, id=course_id, instructor=request.user)
    enrollments = Enrollment.objects.filter(course=course).select_related("student")
    progress_list = []

    total_lectures = Lecture.objects.filter(module__course=course).count()

    for e in enrollments:
        completed_lectures = LectureProgress.objects.filter(
            student=e.student,
            lecture__module__course=course,
            completed=True
        ).count()

        percent = 0
        if total_lectures > 0:
            percent = int((completed_lectures / total_lectures) * 100)

        progress_list.append({
            "student": e.student,
            "completed": completed_lectures,
            "total": total_lectures,
            "percent": percent,
        })

    completed_students = Certificate.objects.filter(course=course)
    downloaded_students = Certificate.objects.filter(
        course=course,
        downloaded_at__isnull=False
    )

    questions = LectureQuestion.objects.filter(
        lecture__module__course=course
    ).select_related("student", "lecture")
    reviews = CourseReview.objects.filter(course=course).order_by("-created_at")

    return render(request, "courses/instructor/course_overview.html", {
        "course": course,
        "progress_list": progress_list,
        "completed_students": completed_students,
        "downloaded_students": downloaded_students,
        "questions": questions,
        "reviews": reviews,

    })


@login_required
def student_history(request, course_id, student_id):
    course = get_object_or_404(Course, id=course_id)
    student = get_object_or_404(User, id=student_id)

    if course.instructor != request.user:
        return render(request, "403.html", status=403)

    lectures = Lecture.objects.filter(module__course=course)
    total_lectures = lectures.count()

    completed_lectures = LectureProgress.objects.filter(
        student=student,
        lecture__in=lectures,
        completed=True
    ).count()

    progress_percent = (
        (completed_lectures / total_lectures * 100) if total_lectures > 0 else 0
    )

    quiz_results = QuizResult.objects.filter(student=student, quiz__course=course).select_related("quiz")

    live_classes = LiveClass.objects.filter(course=course)
    attendance_list = LiveClassAttendance.objects.filter(
        live_class__in=live_classes, user=student
    ).select_related("live_class")

    total_classes = live_classes.count()
    attended = attendance_list.count()
    missed = total_classes - attended

    activity = LectureProgress.objects.filter(
       student=student,
       lecture__in=lectures).select_related("lecture")

    total_watch_time = activity.aggregate(
    total=Sum("last_position"))["total"] or 0


    questions = LectureQuestion.objects.filter(
        student=student,
        lecture__module__course=course).select_related("lecture")

    login_history = LoginHistory.objects.filter(
          user=student).order_by("-login_time")


    context = {
        "course": course,
        "student": student,
        "progress_percent": progress_percent,
        "total_lectures": total_lectures,
        "completed_lectures": completed_lectures,
        "quiz_results": quiz_results,
        "attendance_list": attendance_list,
        "total_classes": total_classes,
        "attended": attended,
        "missed": missed,
        "activity": activity,
        "total_watch_time": total_watch_time,
        "questions": questions,
        "login_history": login_history,
    }

    return render(request, "courses/instructor/student_history.html", context)


@login_required
def instructor_recent_notifications(request):
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]

    unread_count = Notification.objects.filter(
        user=request.user, is_read=False
    ).count()

    data = {
        "unread": unread_count,
        "notifications": [
            {
                "id": n.id,
                "message": n.message,
                "created_at": n.created_at.strftime("%b %d, %I:%M %p"),
                "is_read": n.is_read,
                "url": n.url or "",
            }
            for n in notifications
        ]
    }

    return JsonResponse(data)

@login_required
def instructor_notifications_page(request):
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by("-created_at")

    unread_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()

    return render(request, "courses/instructor/instructor_notifications.html", {
        "notifications": notifications,
        "unread_count": unread_count,
    })

@login_required
def instructor_mark_read(request, notif_id):
    Notification.objects.filter(
        id=notif_id,
        user=request.user
    ).update(is_read=True)

    return JsonResponse({"status": "ok"})

@login_required
def instructor_mark_all_read(request):
    Notification.objects.filter(
        user=request.user,
        is_read=False
    ).update(is_read=True)

    return JsonResponse({"status": "ok"})

@login_required
def instructor_account_settings(request):
    if request.user.role != "instructor":
        return redirect("login")

    user = request.user

    profile, created = InstructorProfile.objects.get_or_create(user=user)

    if request.method == 'POST':

        if 'update_profile' in request.POST:
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)
            user.email = request.POST.get('email', user.email)
            user.save()

            # Instructor-specific fields
            profile.phone = request.POST.get('phone', profile.phone)
            profile.about_me = request.POST.get('about_me', profile.about_me)
            profile.professional_title = request.POST.get('professional_title', profile.professional_title)
            profile.expertise = request.POST.get('expertise', profile.expertise)
            exp = request.POST.get('experience')
            profile.experience = int(exp) if exp.isdigit() else None
            profile.gender = request.POST.get('gender', profile.gender)
            profile.date_of_birth = request.POST.get('date_of_birth', profile.date_of_birth)
            profile.qualification = request.POST.get('qualification', profile.qualification)

            if 'profile_picture' in request.FILES:
                profile.profile_picture = request.FILES['profile_picture']

            profile.save()

            messages.success(request, "Profile updated successfully!")
            return redirect('instructor:account_settings')

        elif 'change_password' in request.POST:
            old_password = request.POST.get('old_password')
            new_password1 = request.POST.get('new_password1')
            new_password2 = request.POST.get('new_password2')

            if not user.check_password(old_password):
                messages.error(request, "Old password is incorrect.")
                return redirect('instructor:account_settings')

            if new_password1 != new_password2:
                messages.error(request, "New passwords do not match.")
                return redirect('instructor:account_settings')

            if len(new_password1) < 8:
                messages.error(request, "Password must be at least 8 characters long.")
                return redirect('instructor:account_settings')

            user.set_password(new_password1)
            user.save()
            update_session_auth_hash(request, user)

            messages.success(request, "Password changed successfully!")
            return redirect('instructor:account_settings')

        elif 'update_notifications' in request.POST:
            messages.success(request, "Notification preferences updated!")
            return redirect('instructor:account_settings')

    return render(request, 'courses/instructor/instructor_account_settings.html', {
        'user': user,
        'profile': profile,
    })

