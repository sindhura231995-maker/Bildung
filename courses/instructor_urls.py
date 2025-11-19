from django.urls import path
from courses import views

app_name = 'instructor'  # <- THIS IS REQUIRED

urlpatterns = [
    # Instructor Dashboard
    path('dashboard/', views.instructor_dashboard, name='instructor_dashboard'),

    # Instructor-only course management
    path('courses/add/', views.add_course, name='add_course'),
    path('courses/<int:course_id>/', views.course_detail, name='course_detail'),
    path('courses/<int:course_id>/add-lecture/', views.add_lecture, name='add_lecture'),
    path('courses/<int:course_id>/feedback/', views.give_feedback, name='give_feedback'),
    path('my-students/', views.my_students, name='my_students'),
    path('student/<int:student_id>/', views.view_student_profile, name='view_student_profile'),

    # Course progress report for instructor
    path('courses/<int:course_id>/progress/', views.course_progress_report, name='course_progress_report'),
    # Instructor course edit
    path('courses/<int:course_id>/edit/', views.course_edit, name='course_edit'),
    # Add Event for a course
    path('courses/<int:course_id>/add-event/', views.add_event, name='add_event'),
    path('schedule_live_class/<int:course_id>/', views.schedule_live_class, name='schedule_live_class'),
    path('my_activity/', views.my_activity, name='my_activity'),
    path("calendar/", views.calendar_view, name="calendar_view"),

]
