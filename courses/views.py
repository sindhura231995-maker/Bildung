from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.dateparse import parse_datetime, parse_date, parse_time

from .models import Course, Enrollment, Lecture, LectureProgress, Feedback, CourseEvent, Module, Certificate,LiveClass
from .forms import CourseForm, LectureForm, FeedbackForm, ModuleFormSet, LiveClassForm
from users.decorators import instructor_required
from django.db.models import Q, Count
from users.models import Profile
from datetime import date
from django.utils import timezone

from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from django.http import FileResponse

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

def student_dashboard(request):
    if request.user.role != "student":
        return redirect("login")
    all_courses = Course.objects.all()
    enrolled_courses = Course.objects.filter(students=request.user)
    return render(request, 'courses/student_dashboard.html', {
        'all_courses': all_courses,
        'enrolled_courses': enrolled_courses
    })

@login_required(login_url='/login/')
def enroll_course(request, course_id):
    """Student: enroll in a course"""
    if getattr(request.user, 'role', None) != 'student':
        return redirect('student_login')

    course = get_object_or_404(Course, id=course_id)
    Enrollment.objects.get_or_create(student=request.user, course=course)
    messages.success(request, f"Enrolled in {course.title}")
    return redirect('student:my_courses')

@login_required
def my_courses(request):
    enrolled_courses = Enrollment.objects.filter(student=request.user).select_related('course')
    return render(request, "courses/student/my_courses.html", {
        "enrolled_courses": enrolled_courses
    })

@login_required(login_url='/student/login/')
def student_course_detail(request, course_id):
    enrollment = get_object_or_404(Enrollment, course_id=course_id, student=request.user)
    course = enrollment.course
    modules = course.modules.prefetch_related('lectures').all()
    lectures = Lecture.objects.filter(module__course=course)

    total = lectures.count()
    completed_lectures = LectureProgress.objects.filter(
        student=request.user,
        lecture__in=lectures,
        completed=True
    ).values_list('lecture_id', flat=True)

    completed = len(completed_lectures)
    progress_map = set(completed_lectures)
    progress_percent = int((completed / total * 100) if total else 0)

    # ✅ Sequential module unlock logic (enhanced)
    unlocked_modules = []
    all_previous_complete = True

    for module in modules:
        if all_previous_complete:
            unlocked_modules.append(module.id)
        else:
            continue

        module_lectures = module.lectures.all()
        module_complete = all(l.id in completed_lectures for l in module_lectures)
        if not module_complete:
            all_previous_complete = False

    return render(request, 'courses/student_course_detail.html', {
        'course': course,
        'modules': modules,
        'lectures': lectures,
        'total': total,
        'completed': completed,
        'progress_map': progress_map,
        'progress_percent': progress_percent,
        'unlocked_modules': unlocked_modules,
    })


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

        # Get current playback info
        watched_time = float(request.POST.get("watched_time", 0))
        duration = float(request.POST.get("duration", 0))

        # Save or update LectureProgress
        progress, created = LectureProgress.objects.update_or_create(
            student=request.user,
            lecture=lecture,
            defaults={
                "completed": True,
                "last_position": duration  # final position = full watch
            }
        )

        # Recalculate course progress
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

    upcoming_classes = (
        LiveClass.objects
        .filter(course_id__in=enrolled_course_ids, date__gte=date.today())
        .select_related('course', 'instructor')
        .order_by('date', 'time')
    )

    upcoming_events = (
        CourseEvent.objects
        .filter(course_id__in=enrolled_course_ids, start_time__gte=timezone.now())
        .select_related('course')
        .order_by('start_time')
    )

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
            "course_id": cls.course.id,
            "backgroundColor": "#0d6efd",
            "borderColor": "#0d6efd",
        })

    for event in upcoming_events:
        events.append({
            "id": event.id,
            "type": "event",
            "title": event.title,
            "event_title": event.title,
            "event_description": event.description,
            "course_name": event.course.title,
            "start": event.start_time.isoformat(),
            "end": event.end_time.isoformat(),
            "course_id": event.course.id,
            "backgroundColor": "#198754",
            "borderColor": "#198754",
        })

    return render(request, 'courses/student/student_calendar.html', {
        'events': events,
    })

# -------------------------------
# Instructor Views
# -------------------------------

@login_required
def instructor_dashboard(request):
    courses = Course.objects.filter(instructor=request.user)

    total_students = Enrollment.objects.filter(
        course__in=courses
    ).values('student').distinct().count()

    return render(request, 'courses/instructor/instructor_dashboard.html', {
        'courses': courses,
        'total_students': total_students,
    })


@login_required
def add_course(request):
    if request.method == 'POST':
        course_form = CourseForm(request.POST, request.FILES)
        if course_form.is_valid():
            course = course_form.save(commit=False)
            course.instructor = request.user
            course.save()

            module_total = int(request.POST.get('modules-TOTAL_FORMS', 0))
            for i in range(module_total):
                title = request.POST.get(f'modules-{i}-title')
                desc = request.POST.get(f'modules-{i}-description')
                if title:
                    module = Module.objects.create(course=course, title=title, description=desc)

                    lecture_index = 0
                    while True:
                        lecture_title = request.POST.get(f'modules-{i}-lectures-{lecture_index}-title')
                        lecture_file = request.FILES.get(f'modules-{i}-lectures-{lecture_index}-video')
                        if not lecture_title:
                            break
                        Lecture.objects.create(module=module, title=lecture_title, video=lecture_file)
                        lecture_index += 1

            return redirect('instructor:instructor_dashboard')
    else:
        course_form = CourseForm()
        module_formset = ModuleFormSet()

    context = {'course_form': course_form, 'module_formset': module_formset}
    return render(request, 'courses/instructor/add_course.html', context)


@login_required
def course_edit(request, course_id):
    """Instructor: edit existing course"""
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
    })

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
            lecture__module__course=course,  # Fixed this line
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
def add_event(request, course_id):
    course = get_object_or_404(Course, id=course_id, instructor=request.user)

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        event_date = request.POST.get('event_date')   
        start_time_raw = request.POST.get('start_time')
        end_time_raw = request.POST.get('end_time')

        event_date_obj = parse_date(event_date)
        start_time = parse_time(start_time_raw)
        end_time = parse_time(end_time_raw)

        start_datetime = datetime.combine(event_date_obj, start_time)
        end_datetime = datetime.combine(event_date_obj, end_time)

        CourseEvent.objects.create(
             course=course,
            title=title,
            description=description,
            date=event_date_obj,        
            start_time=start_datetime,
            end_time=end_datetime)

        messages.success(request, "Event added successfully.")
        return redirect('instructor:course_detail', course_id=course.id)

    return render(request, 'courses/instructor/add_event.html', {'course': course})




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
def add_course(request):
    if request.method == 'POST':
        course_form = CourseForm(request.POST, request.FILES)
        if course_form.is_valid():
            course = course_form.save(commit=False)
            course.instructor = request.user

            # Added line to explicitly set the category from form or POST
            selected_category = request.POST.get('category')
            other_category = request.POST.get('other_category')

            if selected_category == "others" and other_category:
                course.category = other_category.strip()
            else:
                course.category = selected_category
            course.save()

            module_total = int(request.POST.get('modules-TOTAL_FORMS', 0))
            for i in range(module_total):
                title = request.POST.get(f'modules-{i}-title')
                desc = request.POST.get(f'modules-{i}-description')
                if title:
                    module = Module.objects.create(course=course, title=title, description=desc)

                    lecture_index = 0
                    while True:
                        lecture_title = request.POST.get(f'modules-{i}-lectures-{lecture_index}-title')
                        lecture_file = request.FILES.get(f'modules-{i}-lectures-{lecture_index}-video')
                        if not lecture_title:
                            break
                        Lecture.objects.create(module=module, title=lecture_title, video=lecture_file)
                        lecture_index += 1

            return redirect('instructor:instructor_dashboard')
    else:
        course_form = CourseForm()
        module_formset = ModuleFormSet()

    context = {'course_form': course_form, 'module_formset': module_formset}
    return render(request, 'courses/instructor/add_course.html', context)

@login_required(login_url='/login/')
def schedule_live_class(request, course_id):
    if request.method == 'POST':
        form = LiveClassForm(request.POST)
        if form.is_valid():
            live_class = form.save(commit=False)
            live_class.instructor = request.user
            live_class.save()
            messages.success(request, f"✅ Live class '{live_class.topic}' scheduled successfully!")
            return redirect('instructor:instructor_dashboard')
        else:
            messages.error(request, "❌ " + str(form.errors.get('__all__', ['Invalid data'])[0]))
    else:
        form = LiveClassForm(initial={'course': course_id})
    return render(request, 'courses/instructor/schedule_live_class.html', {'form': form})

@login_required(login_url='/login/')
def my_activity(request):
    live_classes = LiveClass.objects.filter(instructor=request.user).order_by('-date', '-time')
    return render(request, 'courses/instructor/my_activity.html', {'live_classes': live_classes})

def calendar_view(request):
    instructor = request.user
    live_classes = LiveClass.objects.filter(course__instructor=instructor, date__gte=date.today())
    events_qs = CourseEvent.objects.filter(course__instructor=instructor, start_time__gte=timezone.now())
    calendar_events = []

    for cls in live_classes:
        calendar_events.append({
            "title": cls.topic,
            "start": f"{cls.date}T{cls.time}",
            "type": "live_class",

            "topic": cls.topic,
            "course_name": cls.course.title,
            "course_id": cls.course.id,

            "backgroundColor": "#0d6efd", 
            "borderColor": "#0d6efd",
        })

    for ev in events_qs:
        calendar_events.append({
            "title": ev.title,  
            "start": ev.start_time.isoformat(),
            "end": ev.end_time.isoformat(),
            "type": "event",

            "event_title": ev.title,
            "event_description": ev.description,
            "course_name": ev.course.title,
            "course_id": ev.course.id,

            "backgroundColor": "#198754",  
            "borderColor": "#198754",
        })

    return render(request, "courses/instructor/instructor_schedule.html", {
        "events": calendar_events,
    })
