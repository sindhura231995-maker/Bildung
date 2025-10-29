from django.urls import path
from . import views
app_name = 'student'  # <- THIS IS REQUIRED
urlpatterns = [
    path('courses/', views.browse_courses, name='browse_courses'),
    path('courses/', views.student_course_list, name='student_course_list'),
    path('courses/<int:course_id>/', views.student_course_detail, name='student_course_detail'),
    path('courses/<int:course_id>/enroll/', views.enroll_course, name='enroll_course'),
    path('lectures/<int:lecture_id>/complete/', views.mark_lecture_complete, name='mark_lecture_complete'),
    path('courses/<int:course_id>/progress/', views.student_progress, name='student_progress'),
]
